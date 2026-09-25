"""Microphone & Wake-Word Diagnostic Tool for Nexus.

Run this script to check your microphone levels, select the right device,
and test real-time 'Hey Jarvis' detection sensitivity.
"""

import sys
import time
import numpy as np
import sounddevice as sd
from openwakeword.model import Model

def list_devices():
    print("\n" + "=" * 60)
    print("           AVAILABLE AUDIO INPUT DEVICES             ")
    print("=" * 60)
    devices = sd.query_devices()
    input_devs = []
    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            input_devs.append((idx, dev))
            default_marker = " [DEFAULT INPUT]" if idx == sd.default.device[0] else ""
            print(f"Device #{idx}: {dev['name']} ({dev['hostapi']}) - Channels: {dev['max_input_channels']}{default_marker}")
    print("=" * 60 + "\n")
    return input_devs

def test_live_wake_word(device_index=None, threshold=0.30):
    dev_name = "Default" if device_index is None else f"Device #{device_index}"
    print(f"Loading 'hey_jarvis' model on {dev_name} (Threshold: {threshold})...")
    
    try:
        oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    sample_rate = 16000
    chunk_size = 1280
    
    print("\n" + "-" * 60)
    print("  SPEAK 'HEY JARVIS' INTO YOUR MIC NOW (Press Ctrl+C to stop) ")
    print("-" * 60)

    max_score_seen = 0.0

    def callback(indata, frames, time_info, status):
        nonlocal max_score_seen
        audio_frame = (indata[:, 0] * 32767).astype(np.int16)
        
        # Audio level (RMS)
        rms = float(np.sqrt(np.mean(indata[:, 0] ** 2))) * 1000
        bar = "#" * min(int(rms / 2), 30)

        preds = oww_model.predict(audio_frame)
        if isinstance(preds, (tuple, list)) and len(preds) > 0:
            preds = preds[0]
        if isinstance(preds, dict):
            score = preds.get("hey_jarvis", 0.0)
        elif isinstance(preds, (int, float)):
            score = float(preds)
        else:
            score = 0.0
        if score > max_score_seen:
            max_score_seen = score

        if score >= threshold:
            print(f"\n🔥 [TRIGGERED!] 'Hey Jarvis' Detected! Score: {score:.3f} >= {threshold}")
            oww_model.reset()
        elif score > 0.10:
            print(f" [Listening...] Score: {score:.3f} | Vol: {rms:4.1f} |{bar.ljust(30)}|")

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=chunk_size,
            device=device_index,
            callback=callback,
        ):
            while True:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"\nStopped test. Peak 'Hey Jarvis' confidence score seen: {max_score_seen:.3f}")
    except Exception as err:
        print(f"\nMicrophone Error on device {device_index}: {err}")

if __name__ == "__main__":
    devs = list_devices()
    selected_device = None
    if len(sys.argv) > 1:
        selected_device = int(sys.argv[1])
    test_live_wake_word(device_index=selected_device)
