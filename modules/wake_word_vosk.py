"""Module for continuous background wake-word detection using Vosk offline speech recognition."""

import json
import os
import queue
import re
import sys
import time
from pathlib import Path
from typing import Callable, List, Optional, Union

import sounddevice as sd
import vosk
from dotenv import load_dotenv

from modules.text_to_speech import speak_text

# Load environment variables
load_dotenv()

# Suppress verbose Vosk C++ internal logging to keep console clean
vosk.SetLogLevel(-1)

# Default wake word triggers: primary ("nexus", "hey nexus") and common phonetic variations/mishearings
DEFAULT_WAKE_WORDS: List[str] = [
    "nexus",
    "hey nexus",
    "next us",
    "nexes",
    "nexis",
    "nexas",
]

# Singleton cache for loaded Vosk Model to prevent redundant disk I/O on repeated listen calls
_CACHED_MODEL: Optional[vosk.Model] = None
_CACHED_MODEL_PATH: Optional[str] = None

# Tracking for diagnostics and state introspection
_last_detected_keyword: Optional[str] = None
_last_partial_transcript: str = ""


def get_last_detected_keyword() -> Optional[str]:
    """Returns the keyword phrase that triggered the most recent wake word detection."""
    return _last_detected_keyword


def get_last_partial_transcript() -> str:
    """Returns the most recent partial/final transcript from the recognizer."""
    return _last_partial_transcript


def _print_missing_model_instructions(attempted_paths: List[str]) -> None:
    """Prints clear, prominent instructions on how and where to download the Vosk model."""
    print("\n" + "=" * 75)
    print(" [VOSK ERROR] Vosk speech recognition model could not be found or loaded!")
    print("=" * 75)
    print(" Nexus requires a Vosk English model for offline 'Nexus' wake-word detection.")
    print(" Checked the following locations:")
    for p in attempted_paths:
        print(f"   - {p}")
    print("\n Quick Setup Instructions:")
    print("   1. Download the lightweight English model (approx 40MB):")
    print("      https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip")
    print("   2. Extract the archive into your project directory as:")
    print("      e:\\aetheris\\model  OR  e:\\aetheris\\vosk-model-small-en-us-0.15")
    print("   3. Or configure VOSK_MODEL_PATH in your .env file to point to its folder.")
    print("=" * 75 + "\n")


def get_vosk_model(model_path: Optional[str] = None) -> Optional[vosk.Model]:
    """Resolves and loads the Vosk Model singleton.

    Checks:
      1. Explicit `model_path` parameter.
      2. `VOSK_MODEL_PATH` from environment/.env.
      3. Project local folders: `model/`, `vosk-model-small-en-us-0.15/`, `models/vosk-model-small-en-us-0.15/`.
      4. Standard Vosk cache via `vosk.Model(model_name="vosk-model-small-en-us-0.15")`.
      5. Fallback to `vosk.Model(lang="en-us")`.

    Returns:
        vosk.Model instance if loaded successfully, or None if missing.
    """
    global _CACHED_MODEL, _CACHED_MODEL_PATH

    if _CACHED_MODEL is not None and (model_path is None or model_path == _CACHED_MODEL_PATH):
        return _CACHED_MODEL

    attempted_paths: List[str] = []

    # 1. Check explicit model_path argument
    if model_path:
        attempted_paths.append(f"Specified path: '{model_path}'")
        if os.path.exists(model_path):
            try:
                _CACHED_MODEL = vosk.Model(model_path)
                _CACHED_MODEL_PATH = model_path
                return _CACHED_MODEL
            except Exception as e:
                print(f"[Vosk Error] Failed loading model from '{model_path}': {e}")

    # 2. Check VOSK_MODEL_PATH env var
    env_path = os.getenv("VOSK_MODEL_PATH")
    if env_path:
        attempted_paths.append(f"VOSK_MODEL_PATH env: '{env_path}'")
        if os.path.exists(env_path):
            try:
                _CACHED_MODEL = vosk.Model(env_path)
                _CACHED_MODEL_PATH = env_path
                return _CACHED_MODEL
            except Exception as e:
                print(f"[Vosk Error] Failed loading model from VOSK_MODEL_PATH ('{env_path}'): {e}")

    # 3. Check local candidate paths relative to workspace or module
    root_dir = Path(__file__).resolve().parent.parent
    local_candidates = [
        root_dir / "model",
        root_dir / "vosk-model-small-en-us-0.15",
        root_dir / "models" / "vosk-model-small-en-us-0.15",
        root_dir / "models" / "model",
        Path("model"),
        Path("vosk-model-small-en-us-0.15"),
    ]

    for candidate in local_candidates:
        c_str = str(candidate.resolve())
        attempted_paths.append(f"Local candidate: '{c_str}'")
        if candidate.exists() and candidate.is_dir():
            try:
                _CACHED_MODEL = vosk.Model(c_str)
                _CACHED_MODEL_PATH = c_str
                return _CACHED_MODEL
            except Exception as e:
                print(f"[Vosk Error] Failed loading model from '{c_str}': {e}")

    # 4. Check Vosk model name / user cache (auto-lookup in ~/.cache/vosk or AppData)
    attempted_paths.append("Vosk cache lookup: 'vosk-model-small-en-us-0.15'")
    try:
        _CACHED_MODEL = vosk.Model(model_name="vosk-model-small-en-us-0.15")
        _CACHED_MODEL_PATH = "vosk-model-small-en-us-0.15"
        return _CACHED_MODEL
    except Exception:
        pass

    # 5. Check language default
    attempted_paths.append("Vosk default language: 'en-us'")
    try:
        _CACHED_MODEL = vosk.Model(lang="en-us")
        _CACHED_MODEL_PATH = "lang:en-us"
        return _CACHED_MODEL
    except Exception:
        pass

    _print_missing_model_instructions(attempted_paths)
    return None


def _matches_wake_word(transcript: str, target_keywords: List[str]) -> Optional[str]:
    """Checks whether the recognized transcript contains any of the target wake word keywords."""
    if not transcript:
        return None

    # Normalize punctuation and whitespace to single spaces
    normalized = re.sub(r"[^\w\s]", " ", transcript.lower())
    words = normalized.split()
    padded_text = f" {' '.join(words)} "

    for kw in target_keywords:
        kw_norm = " ".join(re.sub(r"[^\w\s]", " ", kw.lower()).split())
        if not kw_norm:
            continue
        # Check phrase match with word boundaries
        if f" {kw_norm} " in padded_text:
            return kw

    return None


def listen_for_wake_word(
    wake_word: Optional[Union[str, List[str]]] = None,
    threshold: Optional[float] = None,
    device: Optional[int] = None,
    callback_on_detect: Optional[Callable[[], None]] = None,
    listen_timeout: Optional[float] = None,
    debug: bool = False,
    model_path: Optional[str] = None,
) -> bool:
    """Continuously listens to microphone audio and triggers when 'Nexus' is spoken using Vosk STT.

    Drop-in replacement for the previous wake-word detection mechanism.

    Args:
        wake_word (Optional[Union[str, List[str]]]): Target wake word or list of wake words
            (defaults to 'nexus' and common phonetic variations).
        threshold (Optional[float]): Preserved for interface compatibility (Vosk uses discrete keyword spotting).
        device (Optional[int]): Input audio device index (defaults to MIC_DEVICE_INDEX env or system default).
        callback_on_detect (Optional[Callable]): Optional function to execute immediately upon detection.
        listen_timeout (Optional[float]): Max listening duration in seconds before returning False (None = continuous).
        debug (bool): If True, prints real-time partial transcription hypotheses.
        model_path (Optional[str]): Custom path to Vosk model folder.

    Returns:
        bool: True if wake word detected, False on timeout, error, or stream interruption.
    """
    global _last_detected_keyword, _last_partial_transcript

    # Determine list of trigger keywords
    if wake_word is None:
        target_keywords = list(DEFAULT_WAKE_WORDS)
    elif isinstance(wake_word, str):
        cleaned = wake_word.strip().lower()
        if cleaned in ("hey_jarvis", "hey jarvis", "jarvis"):
            # Gracefully adapt legacy wake-word references to "nexus"
            target_keywords = list(DEFAULT_WAKE_WORDS)
        else:
            target_keywords = [cleaned]
            # Ensure "nexus" variations are present if "nexus" was requested
            if "nexus" in cleaned:
                for kw in DEFAULT_WAKE_WORDS:
                    if kw not in target_keywords:
                        target_keywords.append(kw)
    else:
        target_keywords = [str(k).strip().lower() for k in wake_word if str(k).strip()]
        if not target_keywords:
            target_keywords = list(DEFAULT_WAKE_WORDS)

    # Resolve audio device
    if device is None:
        env_dev = os.getenv("MIC_DEVICE_INDEX")
        if env_dev is not None and env_dev.strip().isdigit():
            device = int(env_dev.strip())

    # Load Vosk Model
    model = get_vosk_model(model_path=model_path)
    if model is None:
        return False

    sample_rate = 16000
    # Create KaldiRecognizer for 16kHz 16-bit mono audio
    try:
        recognizer = vosk.KaldiRecognizer(model, float(sample_rate))
        recognizer.SetWords(False)
    except Exception as rec_err:
        print(f"[Wake-Word Error] Failed to initialize Vosk KaldiRecognizer: {rec_err}")
        return False

    audio_queue: queue.Queue = queue.Queue(maxsize=100)
    dev_info = f"Device #{device}" if device is not None else "Default Microphone"
    keywords_summary = ", ".join([f"'{k}'" for k in target_keywords[:3]])
    print(f"[Wake-Word Engine (Vosk)] Listening continuously for {keywords_summary}... on {dev_info}")

    start_time = time.time()
    last_audio_time = time.time()
    detected = False
    _last_detected_keyword = None
    _last_partial_transcript = ""
    stream_error: Optional[Exception] = None

    def audio_callback(indata, frames, time_info, status):
        nonlocal last_audio_time
        if status:
            if "overflow" not in str(status).lower() and "underflow" not in str(status).lower():
                print(f"[Wake-Word Warning] Stream status: {status}")
        last_audio_time = time.time()
        try:
            audio_queue.put_nowait(bytes(indata))
        except queue.Full:
            # Drop older frames if queue is full to prevent latency buildup
            try:
                audio_queue.get_nowait()
                audio_queue.put_nowait(bytes(indata))
            except Exception:
                pass

    try:
        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=4000,  # ~250ms chunks for low CPU overhead
            device=device,
            dtype="int16",
            channels=1,
            callback=audio_callback,
        ) as stream:
            while not detected:
                # 1. Stream hardware liveness check
                if not stream.active:
                    print("[Wake-Word Error] Audio stream became inactive or was aborted.")
                    return False

                # 2. Stall detection (mic unplugged or audio thread hung > 4.0s)
                if (time.time() - last_audio_time) > 4.0:
                    print("[Wake-Word Warning] Audio stream stalled (no audio packets for >4.0s). Resetting stream...")
                    return False

                # 3. User timeout check
                if listen_timeout and (time.time() - start_time) >= listen_timeout:
                    if debug:
                        print(f"[Wake-Word Engine] Listening timed out after {listen_timeout:.1f}s.")
                    break

                # 4. Fetch audio chunk from queue
                try:
                    data = audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # 5. Process audio in Vosk recognizer
                if recognizer.AcceptWaveform(data):
                    res_raw = recognizer.Result()
                    try:
                        res_json = json.loads(res_raw)
                        transcript = res_json.get("text", "")
                    except Exception:
                        transcript = ""
                else:
                    partial_raw = recognizer.PartialResult()
                    try:
                        partial_json = json.loads(partial_raw)
                        transcript = partial_json.get("partial", "")
                    except Exception:
                        transcript = ""

                if transcript:
                    _last_partial_transcript = transcript
                    if debug:
                        print(f"[Vosk Partial] \"{transcript}\"")

                    matched_kw = _matches_wake_word(transcript, target_keywords)
                    if matched_kw:
                        detected = True
                        _last_detected_keyword = matched_kw
                        print(f"\n-> [Wake Word Detected: 'Nexus' (Matched: '{matched_kw}')]")
                        print("-> Switching to command-listening mode...")
                        recognizer.Reset()
                        break

        # If wake word triggered, play acknowledgment and fire callback
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

    except KeyboardInterrupt:
        try:
            sd.stop()
        except Exception:
            pass
        raise
    except sd.PortAudioError as pa_err:
        print(f"[Wake-Word Error] PortAudio microphone error: {pa_err}")
        return False
    except Exception as err:
        print(f"[Wake-Word Error] Stream exception: {err}")
        return False
    finally:
        # Flush queue and reset recognizer
        while not audio_queue.empty():
            try:
                audio_queue.get_nowait()
            except Exception:
                pass


# Alias for explicit naming
listen_for_wake_word_vosk = listen_for_wake_word


if __name__ == "__main__":
    print("=" * 60)
    print("  Testing Vosk Wake-Word Detection for 'Nexus'")
    print("  Say 'Nexus' or 'Hey Nexus' to trigger...")
    print("=" * 60)
    result = listen_for_wake_word(listen_timeout=15.0, debug=True)
    print(f"Wake word detected result: {result}")
