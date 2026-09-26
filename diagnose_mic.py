"""Microphone & Wake-Word Diagnostic Tool for Nexus.

Run this script to check your microphone levels, select the right device,
and test real-time 'Nexus' / 'Hey Nexus' keyword detection with Vosk.
"""

import json
import queue
import sys
import time
import sounddevice as sd
import vosk

from modules.wake_word_vosk import (
    DEFAULT_WAKE_WORDS,
    _matches_wake_word,
    get_vosk_model,
)

vosk.SetLogLevel(-1)


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


def test_live_wake_word(device_index=None):
    dev_name = "Default" if device_index is None else f"Device #{device_index}"
    print(f"Loading Vosk model for {dev_name}...")

    model = get_vosk_model()
    if model is None:
        print("[Error] Failed to load Vosk model. Please check setup.")
        return

    sample_rate = 16000
    recognizer = vosk.KaldiRecognizer(model, float(sample_rate))
    audio_queue = queue.Queue(maxsize=100)

    print("\n" + "-" * 60)
    print("  SPEAK 'NEXUS' OR 'HEY NEXUS' INTO YOUR MIC (Ctrl+C to stop) ")
    print("-" * 60)

    def callback(indata, frames, time_info, status):
        try:
            audio_queue.put_nowait(bytes(indata))
        except Exception:
            pass

    trigger_count = 0

    try:
        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=4000,
            device=device_index,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            while True:
                try:
                    data = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if recognizer.AcceptWaveform(data):
                    res = json.loads(recognizer.Result())
                    text = res.get("text", "")
                else:
                    pres = json.loads(recognizer.PartialResult())
                    text = pres.get("partial", "")

                if text:
                    matched = _matches_wake_word(text, DEFAULT_WAKE_WORDS)
                    if matched:
                        trigger_count += 1
                        print(f"\n🔥 [TRIGGERED #{trigger_count}!] Wake Word Detected: '{matched}' in \"{text}\"")
                        recognizer.Reset()
                    else:
                        print(f" [Listening...] Recognized: \"{text}\"")

    except KeyboardInterrupt:
        print(f"\nStopped test. Total 'Nexus' triggers detected: {trigger_count}")
    except Exception as err:
        print(f"\nMicrophone Error on device {device_index}: {err}")


if __name__ == "__main__":
    devs = list_devices()
    selected_device = None
    if len(sys.argv) > 1:
        selected_device = int(sys.argv[1])
    test_live_wake_word(device_index=selected_device)
