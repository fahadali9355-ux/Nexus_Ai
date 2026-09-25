"""Verification script for Fix B routing heuristics and keyword clash resolution."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from main import identify_handler, parse_intent


def test_routing_cases():
    test_cases = [
        # 3 cases that must route to Gemini despite containing 'what is' or 'who is'
        ("explain what is quantum computing", "Gemini", "Contains generative verb 'explain'"),
        ("write a poem about who is Ada Lovelace", "Gemini", "Contains creative verb 'write'"),
        ("how does what is known as photosynthesis work", "Gemini", "Contains complex reasoning word 'how'"),
        # 2 cases that must route to Wikipedia
        ("who is Albert Einstein", "Wikipedia", "Concise definitional query (2 words topic)"),
        ("what is photosynthesis", "Wikipedia", "Concise definitional query (1 word topic)"),
        # Additional validation cases
        ("give me the latest news", "News", "Standalone news intent"),
        ("top headlines today", "News", "Standalone headlines intent"),
        ("why is the sky blue", "Gemini", "Complex reasoning 'why'"),
        ("tell me a story about space", "Gemini", "Generative story request"),
        ("wiki Marie Curie", "Wikipedia", "Explicit wiki trigger with concise topic"),
    ]

    print("\n" + "=" * 65)
    print("       AETHERIS FIX B: COMMAND ROUTING HEURISTICS TEST        ")
    print("=" * 65)

    all_passed = True
    for phrase, expected, rationale in test_cases:
        actual = identify_handler(phrase)
        passed = (actual == expected)
        if not passed:
            all_passed = False
        mark = "[PASS]" if passed else "[FAIL]"
        print(f"{mark} | Query: \"{phrase}\"")
        print(f"       Expected: {expected.ljust(10)} | Actual: {actual.ljust(10)} | Rationale: {rationale}\n")

    assert all_passed, "Some routing test cases failed!"
    print("=" * 65)
    print("  ALL 10 ROUTING TEST CASES PASSED WITH 100% ACCURACY!  ")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    test_routing_cases()
