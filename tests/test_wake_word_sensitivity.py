"""Diagnostic test script to measure wake word confidence scores and tune sensitivity."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from modules.wake_word import listen_for_wake_word


def run_sensitivity_test(duration: float = 30.0):
    print("\n" + "=" * 75)
    print("        AETHERIS WAKE WORD SENSITIVITY & CONFIDENCE DIAGNOSTIC        ")
    print("=" * 75)
    print("\n[INSTRUCTIONS]")
    print(f"Say 'Hey Jarvis' several times with natural pronunciation variations")
    print(f"over the next {int(duration)} seconds. Watch the printed confidence scores.\n")
    print("-" * 75)

    # Call with threshold=0.0 and debug=True so it logs scores without auto-triggering
    listen_for_wake_word(
        wake_word="hey_jarvis",
        threshold=0.0,
        debug=True,
        listen_timeout=duration,
    )

    max_score = getattr(listen_for_wake_word, "last_max_score", 0.0)
    recommended_threshold = round(max_score * 0.7, 2)

    print("\n" + "=" * 75)
    print("                       DIAGNOSTIC SUMMARY                             ")
    print("=" * 75)
    print(f"  MAX Confidence Score Observed: {max_score:.3f}")
    print(
        f"  Recommendation: Based on your max observed score of {max_score:.3f}, a recommended\n"
        f"  threshold would be around {recommended_threshold:.2f} (max_score * 0.7) to reliably catch your\n"
        f"  pronunciation while avoiding false positives."
    )
    print("=" * 75 + "\n")


if __name__ == "__main__":
    test_duration = 30.0
    if len(sys.argv) > 1:
        try:
            test_duration = float(sys.argv[1])
        except ValueError:
            test_duration = 30.0
    run_sensitivity_test(duration=test_duration)
