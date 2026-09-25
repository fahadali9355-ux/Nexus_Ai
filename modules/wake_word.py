"""Module for continuous background wake-word detection using openwakeword with resilient error recovery."""

import time
from collections import deque
from typing import Any, Callable, Optional
import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from modules.text_to_speech import speak_text


import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def _extract_wake_score(predictions: Any, target_key: str) -> float:
    """Safely extracts confidence score from model prediction output.

    Handles dicts, tuples (e.g. (pred_dict, timing_dict)), lists, scalars, or numpy arrays.
    """
    if isinstance(predictions, (tuple, list)):
        if len(predictions) == 0:
            return 0.0
        first_item = predictions[0]
        if isinstance(first_item, dict):
            predictions = first_item
        elif isinstance(first_item, (int, float, np.floating, np.integer)):
            return float(first_item)
        elif isinstance(first_item, (list, np.ndarray)):
            arr = np.asarray(first_item)
            return float(arr.flat[0]) if arr.size > 0 else 0.0

    if isinstance(predictions, dict):
        if target_key in predictions:
            return float(predictions[target_key])
        # Check for partial or normalized key match
        norm_target = target_key.lower().replace(" ", "_")
        for k, v in predictions.items():
            norm_k = str(k).lower().replace(" ", "_")
            if norm_target in norm_k or norm_k in norm_target:
                return float(v)
        # If model only contains one output class, use that value
        if len(predictions) == 1:
            return float(next(iter(predictions.values())))
        return 0.0

    if isinstance(predictions, (int, float, np.floating, np.integer)):
        return float(predictions)

    if isinstance(predictions, np.ndarray):
        return float(predictions.flat[0]) if predictions.size > 0 else 0.0

    return 0.0


# Module-level tracking for maximum confidence score observed during listening
_last_max_score: float = 0.0


def get_last_max_score() -> float:
    """Returns the maximum wake-word confidence score observed during the most recent listening session."""
    return _last_max_score


def _update_last_max_score(score: float) -> None:
    """Safely records the maximum observed score in module state and on the function object."""
    global _last_max_score
    _last_max_score = score
    setattr(listen_for_wake_word, "last_max_score", score)


# TODO: Replace with custom-trained "nexus" wake word model once training 
# is complete via openWakeWord's Colab notebook. Currently using 
# "hey_jarvis" as a placeholder detection model.
def listen_for_wake_word(
    wake_word: str = "hey_jarvis",
    threshold: Optional[float] = None,
    device: Optional[int] = None,
    callback_on_detect: Optional[Callable[[], None]] = None,
    listen_timeout: Optional[float] = None,
    debug: bool = False,
) -> bool:
    """Continuously streams audio from microphone and checks for the wake word with stream resilience.

    Args:
        wake_word (str): Target wake word model key (default 'hey_jarvis').
        threshold (Optional[float]): Confidence score trigger threshold (default from env WAKE_WORD_THRESHOLD or 0.30).
        device (Optional[int]): Input audio device index (default from env MIC_DEVICE_INDEX or system default).
        callback_on_detect (Optional[Callable]): Function to execute when wake word triggers.
        listen_timeout (Optional[float]): Max listening duration in seconds (None for continuous).
        debug (bool): When True, prints live confidence scores for audio chunks exceeding 0.05.

    Returns:
        bool: True if wake word detected, False if timed out, interrupted, or stream failed.
    """
    if threshold is None:
        try:
            threshold = float(os.getenv("WAKE_WORD_THRESHOLD", "0.30"))
        except ValueError:
            threshold = 0.30

    if device is None:
        env_dev = os.getenv("MIC_DEVICE_INDEX")
        if env_dev is not None and env_dev.strip().isdigit():
            device = int(env_dev.strip())

    sample_rate = 16000
    chunk_size = 1280  # 80ms audio frames at 16kHz
    pre_buffer = deque(maxlen=sample_rate)  # 1-second rolling pre-buffer

    # Safe model initialization with explicit ONNX/model error capture
    try:
        oww_model = Model(wakeword_models=[wake_word], inference_framework="onnx")
    except Exception as model_err:
        print(f"[Wake-Word Error] Failed to initialize openwakeword model ('{wake_word}'): {model_err}")
        return False

    dev_info = f"Device #{device}" if device is not None else "Default Microphone"
    print(f"[Wake-Word Engine] Listening continuously for '{wake_word}' on {dev_info} (Sensitivity Threshold: {threshold})...")

    start_time = time.time()
    last_audio_time = time.time()
    detected = False
    max_observed_score = 0.0
    callback_exception: Optional[Exception] = None

    def audio_callback(indata, frames, time_info, status):
        nonlocal detected, last_audio_time, callback_exception, max_observed_score
        try:
            last_audio_time = time.time()
            if status:
                # Handle PortAudio buffer underflow/overflow warnings without aborting
                if "overflow" in str(status).lower() or "underflow" in str(status).lower():
                    pass
                else:
                    print(f"[Wake-Word Warning] Stream status: {status}")

            if detected:
                return

            # Convert float32 array to 16-bit PCM numpy array expected by openwakeword
            audio_frame = (indata[:, 0] * 32767).astype(np.int16)

            # Store in rolling pre-buffer
            pre_buffer.extend(audio_frame)

            # Predict wake word probability
            predictions = oww_model.predict(audio_frame)
            score = _extract_wake_score(predictions, wake_word)

            if score > max_observed_score:
                max_observed_score = score

            if debug and score > 0.05:
                print(f"[DEBUG] Live score: {score:.3f} (threshold: {threshold})")

            if threshold > 0.0 and score >= threshold and not detected:
                detected = True
                print(f"\n-> [Wake Word Detected: '{wake_word}' (Confidence: {score:.2f})]")
                print("-> Switching to command-listening mode...")
                oww_model.reset()

        except Exception as cb_err:
            callback_exception = cb_err

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=chunk_size,
            device=device,
            callback=audio_callback,
        ) as stream:
            while not detected:
                # 1. Check if callback caught an internal exception
                if callback_exception:
                    print(f"[Wake-Word Error] Internal audio callback exception: {callback_exception}")
                    return False

                # 2. Check stream hardware liveness (handles USB mic disconnect)
                if not stream.active:
                    print("[Wake-Word Error] Audio stream became inactive or was aborted.")
                    return False

                # 3. Stream stall detection: check if audio data stopped arriving for >4.0s
                if (time.time() - last_audio_time) > 4.0:
                    print("[Wake-Word Warning] Audio stream stalled (no audio packets for >4.0s). Resetting stream...")
                    return False

                # 4. Check user-specified timeout
                if listen_timeout and (time.time() - start_time) >= listen_timeout:
                    print(f"[Wake-Word Engine] Listening timed out after {listen_timeout} seconds.")
                    break

                time.sleep(0.05)

        if detected:
            print("-> Speaking acknowledgment: 'Yes sir'...")
            try:
                speak_text("Yes sir")
            except Exception as tts_err:
                print(f"[Wake-Word Warning] Acknowledgment speech failed: {tts_err}")

            if callback_on_detect:
                try:
                    callback_on_detect()
                except Exception as cb_err:
                    print(f"[Wake-Word Warning] Callback on detect exception: {cb_err}")

        return detected

    except sd.PortAudioError as pa_err:
        print(f"[Wake-Word Error] PortAudio microphone error (device unavailable or disconnected): {pa_err}")
        return False
    except Exception as err:
        print(f"[Wake-Word Error] Stream exception: {err}")
        return False
    finally:
        _update_last_max_score(max_observed_score)


# Initialize attribute on function object for safe runtime access
setattr(listen_for_wake_word, "last_max_score", 0.0)


if __name__ == "__main__":
    print("Testing continuous background listening for 'hey jarvis'...")
    detected = listen_for_wake_word(wake_word="hey_jarvis", threshold=0.5, listen_timeout=15.0)
    print(f"Wake word detected result: {detected}")
