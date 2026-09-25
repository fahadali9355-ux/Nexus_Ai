"""Verification script for Fix A (Silence Detection) and Fix C (Wake Word Resilience)."""

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from modules.audio_input import record_audio_with_silence_detection, record_audio
from modules.wake_word import listen_for_wake_word


def test_fix_a_silence_detection():
    print("\n" + "=" * 65)
    print("  TESTING FIX A: VARIABLE-LENGTH AUDIO RECORDING & SILENCE DETECTION  ")
    print("=" * 65)

    test_file = "test_silence_verification.wav"
    if os.path.exists(test_file):
        os.remove(test_file)

    # Test short recording with 1.5s max duration cap for automated test
    print("[Fix A Test] Starting record_audio_with_silence_detection (min: 1.0s, max: 2.0s)...")
    start_t = time.time()
    out_file = record_audio_with_silence_detection(
        output_filename=test_file,
        min_duration=1.0,
        max_duration=2.0,
        silence_duration=0.8,
    )
    elapsed = time.time() - start_t

    assert out_file and os.path.exists(out_file), "Audio file was not generated"
    file_size = os.path.getsize(out_file)
    print(f"[Fix A Result] Recorded file: {out_file} (Duration: {elapsed:.2f}s, File Size: {file_size} bytes)")
    assert file_size > 10000, f"Audio file size ({file_size} bytes) too small"
    print("[Fix A Status] -> PASS: Variable-length silence detection recording verified.\n")


def test_fix_c_wake_word_resilience():
    print("=" * 65)
    print("  TESTING FIX C: WAKE WORD TIMEOUT & HARDWARE STREAM RESILIENCE   ")
    print("=" * 65)

    # 1. Test timeout handling
    print("[Fix C Test 1] Testing listen_for_wake_word with 2.0s timeout...")
    start_t = time.time()
    result = listen_for_wake_word(wake_word="hey_jarvis", threshold=0.5, listen_timeout=2.0)
    elapsed = time.time() - start_t
    print(f"[Fix C Result 1] Listener timed out cleanly after {elapsed:.2f}s (Result: {result})")
    assert result is False, "Listener should return False on timeout without wake word"
    assert 1.8 <= elapsed <= 3.5, f"Timeout took unexpected duration ({elapsed:.2f}s)"
    print("[Fix C Status 1] -> PASS: Timeout cleanly handled without hanging.")

    # 2. Test invalid model key exception handling
    print("\n[Fix C Test 2] Testing listen_for_wake_word with nonexistent model key...")
    safe_result = listen_for_wake_word(wake_word="nonexistent_invalid_model_12345", listen_timeout=1.0)
    print(f"[Fix C Result 2] Safe return on invalid model key: {safe_result}")
    assert safe_result is False, "Listener should return False gracefully on model error"
    print("[Fix C Status 2] -> PASS: Model exception safely caught and returned False.\n")

    print("=" * 65)
    print("  ALL FIX A & FIX C RESILIENCE TESTS PASSED!  ")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    test_fix_a_silence_detection()
    test_fix_c_wake_word_resilience()
