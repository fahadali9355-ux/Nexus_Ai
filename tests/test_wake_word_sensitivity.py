"""Diagnostic test script to test and verify Vosk 'Nexus' wake word spotting."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from modules.wake_word_vosk import (
    DEFAULT_WAKE_WORDS,
    get_last_detected_keyword,
    get_last_partial_transcript,
    listen_for_wake_word,
)


def run_wake_word_test(duration: float = 20.0):
    print("\n" + "=" * 75)
    print("           NEXUS VOSK WAKE WORD KEYWORD SPOTTING TEST                 ")
    print("=" * 75)
    print("\n[INSTRUCTIONS]")
    print("Say 'Nexus' or 'Hey Nexus' (or variations like 'next us') into your microphone.")
    print(f"Listening for up to {int(duration)} seconds with debug transcript output enabled.\n")
    print("-" * 75)

    detected = listen_for_wake_word(
        wake_word=DEFAULT_WAKE_WORDS,
        debug=True,
        listen_timeout=duration,
    )

    matched_kw = get_last_detected_keyword()
    transcript = get_last_partial_transcript()

    print("\n" + "=" * 75)
    print("                       DIAGNOSTIC SUMMARY                             ")
    print("=" * 75)
    print(f"  Wake Word Detected: {detected}")
    print(f"  Matched Keyword:    {matched_kw}")
    print(f"  Last Transcript:    \"{transcript}\"")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    test_duration = 20.0
    if len(sys.argv) > 1:
        try:
            test_duration = float(sys.argv[1])
        except ValueError:
            test_duration = 20.0
    run_wake_word_test(duration=test_duration)
