"""Module for converting text responses into spoken audio using Piper offline neural TTS engine."""

import os
import re
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from piper import PiperVoice, SynthesisConfig

# Load environment variables
load_dotenv()

# Voices directory path relative to this file
VOICES_DIR = Path(__file__).resolve().parent / "piper_voices"

# Default Voice Configurations
DEFAULT_EN_VOICE_NAME = os.getenv("PIPER_VOICE_NAME", "en_US-lessac-medium")
DEFAULT_UR_VOICE_NAME = os.getenv("PIPER_URDU_VOICE_NAME", "ur_PK-fasih-medium")

# Speech speed configuration (SynthesisConfig length_scale)
# 1.0 is standard pace, 0.90 - 0.95 corresponds to ~200 WPM equivalent (faster, brisk delivery)
DEFAULT_LENGTH_SCALE = float(os.getenv("PIPER_LENGTH_SCALE", "0.95"))

# Multi-voice dictionary cache: {voice_name_key: PiperVoice}
_VOICE_CACHE = {}


def is_urdu_text(text: str, threshold: float = 0.20) -> bool:
    """Lightweight check to determine if text is primarily in Urdu / Arabic script.

    Scans Unicode blocks:
      - Arabic/Urdu: U+0600 - U+06FF
      - Arabic Supplement: U+0750 - U+077F
      - Arabic Extended-A: U+08A0 - U+08FF
      - Arabic Presentation Forms: U+FB50 - U+FDFF, U+FE70 - U+FEFF

    Args:
        text (str): Input text string.
        threshold (float): Minimum ratio of Urdu-script characters over total alphabetic characters.

    Returns:
        bool: True if text contains significant Urdu script, False otherwise.
    """
    if not text or not text.strip():
        return False

    alpha_chars = [
        c for c in text
        if not c.isspace() and not c.isdigit() and c not in ".,!?:;\"'()[]{}<>-—_۔؟"
    ]
    if not alpha_chars:
        return False

    urdu_count = sum(
        1 for c in alpha_chars
        if (
            "\u0600" <= c <= "\u06FF"
            or "\u0750" <= c <= "\u077F"
            or "\u08A0" <= c <= "\u08FF"
            or "\uFB50" <= c <= "\uFDFF"
            or "\uFE70" <= c <= "\uFEFF"
        )
    )

    ratio = urdu_count / len(alpha_chars)
    return ratio >= threshold


def clean_text_for_speech(text: str) -> str:
    """Strips Markdown syntax and formatting artifacts from text before TTS speech synthesis.

    Removes markdown markers (**, *, #, ``, tables, bullets, links, etc.) while preserving
    natural sentence punctuation (. , ? ! : ; ' " ۔ ؟) for accurate TTS prosody and pause pacing.

    Args:
        text (str): Raw input text potentially containing Markdown syntax.

    Returns:
        str: Clean plain-text string ready for natural speech synthesis.
    """
    if not text or not text.strip():
        return ""

    cleaned = text

    # 1. Code blocks (triple backticks) - remove wrapper, retain code content
    cleaned = re.sub(r"```[a-zA-Z0-9_\-\+]*\n?([\s\S]*?)```", r" \1 ", cleaned)

    # 2. Inline code backticks (`code` -> code)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)

    # 3. Images ![alt](url) -> alt
    cleaned = re.sub(r"!\[([^\]]*)\]\([^\)]+\)", r"\1", cleaned)

    # 4. Links [text](url) -> text (drop URL so TTS doesn't read http/web links)
    cleaned = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", cleaned)

    # 5. Strip raw HTML tags if present (<br>, <b>, etc.)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)

    # 6. Remove Markdown table divider lines (e.g. |---|---|)
    cleaned = re.sub(r"^[ \t\-:|]+$", "", cleaned, flags=re.MULTILINE)
    # Remove remaining table pipe delimiters
    cleaned = re.sub(r"\|", " ", cleaned)

    # 7. Remove headers (e.g. ### Heading -> Heading)
    cleaned = re.sub(r"^\s*#{1,6}\s+", "", cleaned, flags=re.MULTILINE)

    # 8. Remove blockquotes (> quote -> quote)
    cleaned = re.sub(r"^\s*>\s+", "", cleaned, flags=re.MULTILINE)

    # 9. Remove horizontal rules (---, ***, ___)
    cleaned = re.sub(r"^\s*[-*_]{3,}\s*$", "", cleaned, flags=re.MULTILINE)

    # 10. Remove bullet points (*, -, + at start of line)
    cleaned = re.sub(r"^\s*[\*\-\+]\s+", "", cleaned, flags=re.MULTILINE)

    # 11. Remove bold, italic, and strikethrough markdown symbols
    # ***text*** or ___text___ -> text
    cleaned = re.sub(r"(\*{1,3}|_{1,3})([^\*_]+?)\1", r"\2", cleaned)
    # ~~text~~ -> text
    cleaned = re.sub(r"~~([^~]+)~~", r"\1", cleaned)

    # 12. Remove any remaining stray markdown asterisks, hashes, or tildes
    cleaned = re.sub(r"[\*#~]", "", cleaned)

    # 13. Convert separate line breaks into natural speech pauses (. ) if not already ending in punctuation
    lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
    formatted_lines = []
    for line in lines:
        if line and line[-1] not in ".!?,;:۔؟":
            line = line + "."
        formatted_lines.append(line)

    cleaned = " ".join(formatted_lines)

    # 14. Clean up spaces and punctuation repetition
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\s+([,.\?!;:۔؟])", r"\1", cleaned)
    cleaned = re.sub(r"\.+", ".", cleaned)

    return cleaned.strip()


def get_piper_voice(
    voice_name_or_path: Optional[str] = None,
) -> Optional[PiperVoice]:
    """Loads and caches Piper neural TTS voice models by name or path.

    Maintains preloaded models in memory to allow instant language/voice switching per request.

    Args:
        voice_name_or_path (Optional[str]): Voice model filename, name, or explicit path.

    Returns:
        PiperVoice instance if successfully loaded, or None if file is missing.
    """
    global _VOICE_CACHE

    target_name = (
        voice_name_or_path
        or os.getenv("PIPER_MODEL_PATH")
        or os.getenv("PIPER_VOICE_NAME", DEFAULT_EN_VOICE_NAME)
    )

    # Normalize cache key
    key = str(target_name).strip()
    if key.endswith(".onnx"):
        key = key[:-5]

    if key in _VOICE_CACHE:
        return _VOICE_CACHE[key]

    # Resolve model file (.onnx) and config file (.onnx.json)
    if os.path.isabs(target_name) or ("/" in target_name or "\\" in target_name):
        model_path = Path(target_name)
    else:
        base_name = target_name[:-5] if target_name.endswith(".onnx") else target_name
        model_path = VOICES_DIR / f"{base_name}.onnx"

    if not model_path.exists():
        # Match candidate in piper_voices dir
        candidates = list(VOICES_DIR.glob(f"*{base_name}*.onnx"))
        if candidates:
            model_path = candidates[0]
        else:
            all_onnx = list(VOICES_DIR.glob("*.onnx"))
            if all_onnx:
                model_path = all_onnx[0]
                print(f"[Piper TTS Notice] Voice '{target_name}' not found. Using available model: '{model_path.name}'.")
            else:
                print("\n" + "=" * 70)
                print("[Error: Piper TTS] No Piper voice model found!")
                print(f"Looked for: {model_path}")
                print(f"Please place an ONNX Piper voice model and .json config inside: {VOICES_DIR}")
                print("=" * 70 + "\n")
                return None

    config_path = Path(f"{model_path}.json")
    if not config_path.exists():
        alt_config = model_path.with_suffix(".onnx.json")
        if alt_config.exists():
            config_path = alt_config

    try:
        voice = PiperVoice.load(
            model_path=str(model_path),
            config_path=str(config_path) if config_path.exists() else None,
        )
        _VOICE_CACHE[key] = voice
        _VOICE_CACHE[model_path.stem] = voice
        print(f"[Piper TTS] Loaded and cached neural voice model: '{model_path.stem}'.")
        return voice
    except Exception as err:
        print(f"[Error: Piper TTS] Failed loading voice from '{model_path}': {err}")
        return None


def preload_voices() -> None:
    """Pre-warms both English and Urdu neural voice models into memory at startup."""
    try:
        get_piper_voice(DEFAULT_EN_VOICE_NAME)
    except Exception as e:
        print(f"[Piper TTS Warning] Failed pre-loading English voice '{DEFAULT_EN_VOICE_NAME}': {e}")

    try:
        get_piper_voice(DEFAULT_UR_VOICE_NAME)
    except Exception as e:
        print(f"[Piper TTS Warning] Failed pre-loading Urdu voice '{DEFAULT_UR_VOICE_NAME}': {e}")


# Automatically preload models on startup
preload_voices()


def speak_text(
    text: str,
    voice_name: Optional[str] = None,
    length_scale: Optional[float] = None,
) -> bool:
    """Synthesizes text into high-quality neural speech using Piper and plays it aloud via sounddevice.

    Automatically detects language (Urdu vs. English) from the cleaned input text
    and selects the optimal preloaded neural voice model without reload latency.

    Args:
        text (str): Input text to synthesize (Markdown formatting is automatically stripped).
        voice_name (Optional[str]): Optional custom voice override.
        length_scale (Optional[float]): Optional custom speech speed factor (<1.0 = faster, >1.0 = slower).

    Returns:
        bool: True if synthesis and playback succeeded, False otherwise.
    """
    if not text or not text.strip():
        return False

    # 1. Strip Markdown artifacts for clean natural speech
    speech_text = clean_text_for_speech(text)
    if not speech_text:
        return False

    # 2. Determine appropriate voice model based on language detection
    if voice_name:
        selected_voice_name = voice_name
    elif is_urdu_text(speech_text):
        selected_voice_name = DEFAULT_UR_VOICE_NAME
    else:
        selected_voice_name = DEFAULT_EN_VOICE_NAME

    # 3. Retrieve pre-cached Piper neural voice model
    voice = get_piper_voice(selected_voice_name)
    if voice is None:
        # Fallback to English if Urdu voice fails, or vice-versa
        voice = get_piper_voice(DEFAULT_EN_VOICE_NAME)
        if voice is None:
            print("[Error: Piper TTS] Voice model is unavailable for speech synthesis.")
            return False

    # 4. Configure synthesis parameters (speed, volume)
    speed = length_scale if length_scale is not None else DEFAULT_LENGTH_SCALE
    syn_config = SynthesisConfig(
        length_scale=speed,
        volume=1.0,
    )

    try:
        # 5. Synthesize speech chunks
        audio_chunks = []
        for chunk in voice.synthesize(speech_text, syn_config=syn_config):
            audio_chunks.append(chunk.audio_int16_array)

        if not audio_chunks:
            return False

        full_audio = np.concatenate(audio_chunks)

        # 6. Play audio buffer directly through sounddevice
        sample_rate = voice.config.sample_rate
        sd.play(full_audio, samplerate=sample_rate)
        sd.wait()
        return True

    except KeyboardInterrupt:
        try:
            sd.stop()
        except Exception:
            pass
        raise
    except sd.PortAudioError as pa_err:
        print(f"[Error: Piper TTS] Audio playback output error (sounddevice): {pa_err}")
        return False
    except Exception as err:
        print(f"[Error: Piper TTS] Synthesis exception: {err}")
        return False


def stop_speech() -> None:
    """Immediately interrupts and stops any ongoing audio playback."""
    try:
        sd.stop()
    except Exception:
        pass


__all__ = [
    "speak_text",
    "clean_text_for_speech",
    "get_piper_voice",
    "is_urdu_text",
    "preload_voices",
    "stop_speech",
    "DEFAULT_EN_VOICE_NAME",
    "DEFAULT_UR_VOICE_NAME",
]


if __name__ == "__main__":
    test_en = "Hello! I am Nexus. My speech synthesis is powered by Piper neural TTS."
    test_ur = "ہیلو! میں آپ کا اسسٹنٹ نیکسس ہوں۔ میں اردو میں بات کر سکتا ہوں۔"

    print(f"English Detection: is_urdu_text('{test_en}') -> {is_urdu_text(test_en)}")
    print(f"Urdu Detection: is_urdu_text('{test_ur}') -> {is_urdu_text(test_ur)}")

    print("\nSynthesizing English sentence...")
    speak_text(test_en)

    print("\nSynthesizing Urdu sentence...")
    speak_text(test_ur)
