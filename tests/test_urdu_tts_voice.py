"""Automated test suite for Multilingual Piper TTS (English & Urdu Voice Switching)."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Ensure UTF-8 output encoding in Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from modules.text_to_speech import (
    is_urdu_text,
    clean_text_for_speech,
    get_piper_voice,
    DEFAULT_EN_VOICE_NAME,
    DEFAULT_UR_VOICE_NAME,
    _VOICE_CACHE,
)
from piper import SynthesisConfig


def test_urdu_language_detection():
    print("\n" + "=" * 70)
    print("        TEST 1: LIGHTWEIGHT URDU SCRIPT DETECTION         ")
    print("=" * 70)

    urdu_phrases = [
        "ہیلو! میں آپ کا اسسٹنٹ نیکسس ہوں۔",
        "پاکستان کا دارالحکومت اسلام آباد ہے۔",
        "آپ کیسے ہیں؟",
        "آج موسم کیسا ہے؟",
        "یہ ایک اردو جملہ ہے۔",
        "**ہیلو**، میں آپ کی کیا مدد کر سکتا ہوں؟",
        "نیکسس، لائٹ بند کر دو۔",
    ]

    english_phrases = [
        "Hello! I am your assistant Nexus.",
        "What is the capital of Pakistan?",
        "How are you today?",
        "The weather is clear and sunny.",
        "Open Instagram in the browser.",
        "Set volume to 50 percent.",
        "Tell me about Albert Einstein.",
    ]

    for urdu in urdu_phrases:
        cleaned = clean_text_for_speech(urdu)
        detected = is_urdu_text(cleaned)
        assert detected, f"Failed to detect Urdu for: '{urdu}'"
        print(f"  [PASS] Urdu Detected: '{urdu[:35]}...' -> is_urdu_text=True")

    for eng in english_phrases:
        cleaned = clean_text_for_speech(eng)
        detected = is_urdu_text(cleaned)
        assert not detected, f"False positive Urdu detection for English: '{eng}'"
        print(f"  [PASS] English Detected: '{eng[:35]}...' -> is_urdu_text=False")

    print("  -> ALL Urdu & English script detections verified (100% accuracy)!\n")


def test_multi_voice_preloading():
    print("=" * 70)
    print("        TEST 2: PRELOADED MULTI-VOICE CACHE VERIFICATION  ")
    print("=" * 70)

    en_voice = get_piper_voice(DEFAULT_EN_VOICE_NAME)
    ur_voice = get_piper_voice(DEFAULT_UR_VOICE_NAME)

    assert en_voice is not None, f"English voice model '{DEFAULT_EN_VOICE_NAME}' failed to load!"
    assert ur_voice is not None, f"Urdu voice model '{DEFAULT_UR_VOICE_NAME}' failed to load!"

    print(f"  [PASS] English Voice loaded: '{DEFAULT_EN_VOICE_NAME}' (Sample Rate: {en_voice.config.sample_rate} Hz)")
    print(f"  [PASS] Urdu Voice loaded: '{DEFAULT_UR_VOICE_NAME}' (Sample Rate: {ur_voice.config.sample_rate} Hz)")

    # Verify both exist in _VOICE_CACHE for zero-latency switching
    assert DEFAULT_EN_VOICE_NAME in _VOICE_CACHE or "en_US-lessac-medium" in _VOICE_CACHE
    assert DEFAULT_UR_VOICE_NAME in _VOICE_CACHE or "ur_PK-fasih-medium" in _VOICE_CACHE

    print("  -> Preloaded multi-voice cache verified in memory!\n")


def test_synthesis_per_language():
    print("=" * 70)
    print("        TEST 3: NEURAL SYNTHESIS FOR BOTH LANGUAGES       ")
    print("=" * 70)

    test_en_text = "Hello! Nexus is operating normally with English speech synthesis."
    test_ur_text = "ہیلو! نیکسس اردو آواز کے ساتھ بالکل ٹھیک کام کر رہا ہے۔"

    # 1. English synthesis
    en_voice = get_piper_voice(DEFAULT_EN_VOICE_NAME)
    syn_config = SynthesisConfig(length_scale=0.95, volume=1.0)
    en_chunks = [c.audio_int16_array for c in en_voice.synthesize(test_en_text, syn_config=syn_config)]
    assert len(en_chunks) > 0, "English synthesis produced 0 audio chunks!"
    en_audio = np.concatenate(en_chunks)
    assert len(en_audio) > 0, "English audio buffer is empty!"
    print(f"  [PASS] English text synthesized: {len(en_audio)} samples ({len(en_audio)/en_voice.config.sample_rate:.2f}s)")

    # 2. Urdu synthesis
    ur_voice = get_piper_voice(DEFAULT_UR_VOICE_NAME)
    ur_chunks = [c.audio_int16_array for c in ur_voice.synthesize(test_ur_text, syn_config=syn_config)]
    assert len(ur_chunks) > 0, "Urdu synthesis produced 0 audio chunks!"
    ur_audio = np.concatenate(ur_chunks)
    assert len(ur_audio) > 0, "Urdu audio buffer is empty!"
    print(f"  [PASS] Urdu text synthesized: {len(ur_audio)} samples ({len(ur_audio)/ur_voice.config.sample_rate:.2f}s)")

    print("  -> Neural synthesis succeeded for both English and Urdu voices!\n")


if __name__ == "__main__":
    test_urdu_language_detection()
    test_multi_voice_preloading()
    test_synthesis_per_language()
    print("=" * 70)
    print("       ALL MULTILINGUAL TTS TESTS PASSED (100% SUCCESS)!  ")
    print("=" * 70 + "\n")
