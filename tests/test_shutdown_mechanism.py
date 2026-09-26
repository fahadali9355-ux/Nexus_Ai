"""Automated test suite for Nexus Graceful Shutdown & Voice-based Stop Commands."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from modules.fast_path import is_shutdown_command, try_local_fast_path
from main import parse_intent, identify_handler, route_and_process
from modules.text_to_speech import stop_speech
from modules.task_executor import cleanup_browser


def test_voice_shutdown_recognition():
    print("\n" + "=" * 70)
    print("        TEST 1: VOICE SHUTDOWN PHRASE RECOGNITION         ")
    print("=" * 70)

    positive_phrases = [
        "nexus stop",
        "stop",
        "please stop",
        "shut down",
        "shutdown",
        "shut down nexus",
        "shutdown nexus",
        "shut down the system",
        "go to sleep",
        "go to sleep nexus",
        "sleep",
        "exit",
        "exit nexus",
        "exit program",
        "quit",
        "quit nexus",
        "terminate",
        "terminate nexus",
        "power off",
        "turn off",
        "goodbye",
        "goodbye nexus",
        "bye nexus",
        "stop listening",
    ]

    for phrase in positive_phrases:
        assert is_shutdown_command(phrase), f"Failed to recognize '{phrase}' as shutdown command!"
        handler, _ = parse_intent(phrase)
        assert handler == "Shutdown", f"Intent for '{phrase}' was [{handler}], expected [Shutdown]!"
        assert identify_handler(phrase) == "Shutdown", f"Handler for '{phrase}' was not 'Shutdown'!"
        resp = route_and_process(phrase)
        assert "shutting down" in resp.lower() or "goodbye" in resp.lower(), f"Unexpected route_and_process response: {resp}"
        fast_resp = try_local_fast_path(phrase)
        assert fast_resp is not None and "shutting down" in fast_resp.lower(), f"Fast-path failed for '{phrase}': {fast_resp}"
        print(f"  [PASS] Phrase: '{phrase:24}' -> Handler: [{handler}] -> Response: \"{resp}\"")

    print("  -> ALL positive voice stop phrases recognized with 100% precision!\n")


def test_voice_shutdown_negatives():
    print("=" * 70)
    print("        TEST 2: NON-SHUTDOWN PHRASES (NEGATIVE TEST)      ")
    print("=" * 70)

    negative_phrases = [
        ("stop music", "Action"),
        ("stop timer", "Action"),
        ("open notepad", "Action"),
        ("open instagram", "Action"),
        ("set volume to 50", "Action"),
        ("what is photosynthesis", "Wikipedia"),
        ("explain how a car stops", "Gemini"),
        ("who is sleeping beauty", "Wikipedia"),
        ("exit interview questions", "Gemini"),
    ]

    for phrase, expected_handler in negative_phrases:
        assert not is_shutdown_command(phrase), f"Phrase '{phrase}' falsely triggered shutdown!"
        handler, _ = parse_intent(phrase)
        assert handler != "Shutdown", f"Phrase '{phrase}' should not be routed to Shutdown!"
        print(f"  [PASS] Phrase: '{phrase:28}' -> Handler: [{handler}] (Correctly not Shutdown)")

    print("  -> ALL negative non-shutdown phrases safely isolated!\n")


def test_subsystem_cleanup_routines():
    print("=" * 70)
    print("        TEST 3: SUBSYSTEM CLEANUP FUNCTIONS               ")
    print("=" * 70)

    # 1. Test stop_speech
    try:
        stop_speech()
        print("  [PASS] stop_speech() executed safely without error.")
    except Exception as e:
        assert False, f"stop_speech() raised unexpected exception: {e}"

    # 2. Test cleanup_browser
    try:
        cleanup_browser()
        print("  [PASS] cleanup_browser() executed safely without error.")
    except Exception as e:
        assert False, f"cleanup_browser() raised unexpected exception: {e}"

    print("  -> Subsystem cleanup hooks verified!\n")


if __name__ == "__main__":
    test_voice_shutdown_recognition()
    test_voice_shutdown_negatives()
    test_subsystem_cleanup_routines()
    print("=" * 70)
    print("       ALL SHUTDOWN & VOICE STOP TESTS PASSED (100%)!     ")
    print("=" * 70 + "\n")
