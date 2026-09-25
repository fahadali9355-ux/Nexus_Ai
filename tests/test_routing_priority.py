"""Test script to verify intent routing priorities in Aetheris."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from main import parse_intent, identify_handler

def run_routing_tests():
    test_cases = [
        ("open notepad", "Action"),
        ("explain how volume controls work", "Gemini"),
        ("write a note about how to open a bank account", "Gemini"),
        ("set volume to 50", "Action"),
        ("take a screenshot", "Action"),
        ("how do I start a business", "Gemini"),
        # Additional sanity checks
        ("lock the computer", "Action"),
        ("lock my pc", "Action"),
        ("create a text file called test.txt with hello", "Action"),
        ("give me the latest news", "News"),
        ("who is Albert Einstein", "Wikipedia"),
        ("what is photosynthesis", "Wikipedia"),
        ("tell me a joke", "Gemini"),
    ]

    print("\n" + "=" * 75)
    print("                 AETHERIS INTENT ROUTING VERIFICATION TEST               ")
    print("=" * 75)

    all_passed = True
    for phrase, expected in test_cases:
        handler = identify_handler(phrase)
        passed = (handler == expected)
        if not passed:
            all_passed = False
        mark = "[PASS]" if passed else "[FAIL]"
        print(f"  {mark} '{phrase:<48}' -> Got: {handler:<10} (Expected: {expected})")

    print("=" * 75)
    if all_passed:
        print("  >>> ALL ROUTING TESTS PASSED! <<<")
    else:
        print("  >>> SOME ROUTING TESTS FAILED! <<<")
    print("=" * 75 + "\n")
    return all_passed

if __name__ == "__main__":
    success = run_routing_tests()
    sys.exit(0 if success else 1)
