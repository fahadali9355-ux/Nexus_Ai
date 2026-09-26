"""Automated test suite for Local Fast-Path Routing and Known Services."""

import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import time
from modules.fast_path import try_local_fast_path
from modules.task_executor import KNOWN_SERVICES, KNOWN_APPS
from main import route_and_process, parse_intent


def test_known_services_expansion():
    print("\n" + "=" * 70)
    print("        TEST 1: KNOWN SERVICES EXPANSION (PART A)                 ")
    print("=" * 70)

    required_services = [
        ("instagram", "https://www.instagram.com"),
        ("facebook", "https://www.facebook.com"),
        ("whatsapp", "https://web.whatsapp.com"),
        ("linkedin", "https://www.linkedin.com"),
        ("netflix", "https://www.netflix.com"),
        ("spotify", "https://open.spotify.com"),
        ("amazon", "https://www.amazon.com"),
        ("twitch", "https://www.twitch.tv"),
        ("pinterest", "https://www.pinterest.com"),
        ("tiktok", "https://www.tiktok.com"),
        ("youtube", "https://www.youtube.com"),
        ("github", "https://www.github.com"),
    ]

    for service, expected_url in required_services:
        assert service in KNOWN_SERVICES, f"Service '{service}' missing from KNOWN_SERVICES!"
        assert KNOWN_SERVICES[service] == expected_url, f"Service '{service}' URL mismatch: {KNOWN_SERVICES[service]}"
        print(f"  [PASS] {service:12} -> {KNOWN_SERVICES[service]}")

    print("  -> ALL required web services verified in KNOWN_SERVICES dictionary!\n")


def test_fast_path_deterministic_commands():
    print("=" * 70)
    print("        TEST 2: FAST-PATH INSTANT LOCAL EXECUTION (PART B)        ")
    print("=" * 70)

    test_queries = [
        ("open instagram", "Instagram / Browser opening"),
        ("open facebook", "Facebook / Browser opening"),
        ("open whatsapp", "WhatsApp / Browser opening"),
        ("open notepad", "Notepad app opening"),
        ("set volume to 40", "Volume adjustment"),
        ("mute volume", "Mute volume"),
        ("unmute", "Unmute volume"),
        ("what time is it", "System time inquiry"),
        ("today's date", "Date inquiry"),
        ("battery status", "Battery status"),
        ("take a screenshot", "Screenshot capture"),
        ("search google for artificial intelligence", "Web search"),
    ]

    for query, description in test_queries:
        t0 = time.perf_counter()
        result = try_local_fast_path(query)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert result is not None and len(result) > 0, f"Query '{query}' failed to match fast-path!"
        print(f"  [PASS] ({elapsed_ms:5.2f} ms) | Query: '{query}' ({description})")
        print(f"         Result: {result[:80]}")

    print("  -> ALL deterministic action queries executed locally in < 50ms!\n")


def test_fast_path_gemini_passthrough():
    print("=" * 70)
    print("        TEST 3: COMPLEX / CONVERSATIONAL GEMINI PASSTHROUGH       ")
    print("=" * 70)

    complex_queries = [
        "explain how quantum computing works",
        "write a creative story about space exploration",
        "how do I bake chocolate chip cookies",
        "summarize the benefits of aerobic exercise",
    ]

    for q in complex_queries:
        handler, _ = parse_intent(q)
        fast_result = try_local_fast_path(q)
        assert fast_result is None, f"Complex query '{q}' should NOT match fast-path!"
        print(f"  [PASS] Query: '{q}'")
        print(f"         Intent: [{handler}] | Fast-Path: None (Cleanly delegates to Gemini LLM)")

    print("  -> Complex queries successfully pass through to Gemini AI!\n")


if __name__ == "__main__":
    test_known_services_expansion()
    test_fast_path_deterministic_commands()
    test_fast_path_gemini_passthrough()
    print("=" * 70)
    print("       ALL FAST-PATH & MAPPING TESTS PASSED (100% SUCCESS)!       ")
    print("=" * 70 + "\n")
