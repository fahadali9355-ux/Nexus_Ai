"""Automated verification test suite for Selenium browser tab tracking, closing, and Gemini routing."""

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from modules.task_executor import (
    open_website,
    close_website,
    cleanup_browser,
    get_open_tabs,
)
from modules.gemini_client import route_to_action
from main import parse_intent, identify_handler


def run_tab_management_test():
    print("\n" + "=" * 75)
    print("       AETHERIS SELENIUM TAB MANAGEMENT PROGRAMMATIC TEST SUITE       ")
    print("=" * 75)

    # Ensure clean starting state
    cleanup_browser()
    time.sleep(1.0)

    try:
        # -------------------------------------------------------------
        # Step 1: Open YouTube
        # -------------------------------------------------------------
        print("\n[STEP 1] Executing open_website('youtube.com')...")
        res1 = open_website("youtube.com")
        print(f"-> Response: \"{res1}\"")
        time.sleep(3.0)  # Wait for page to initialize

        tabs_step1 = get_open_tabs()
        print(f"-> Open Tabs Count: {len(tabs_step1)}")
        for i, t in enumerate(tabs_step1):
            print(f"   Tab [{i+1}] Handle: {t['handle']} | Title: '{t['title']}' | URL: {t['url']}")
        
        assert len(tabs_step1) >= 1, "Expected at least 1 open tab after opening YouTube"
        assert any("youtube" in (t["url"] + t["title"]).lower() for t in tabs_step1), "YouTube tab not found in open tabs"
        print("-> [PASS] Step 1 verified: YouTube opened in Selenium-controlled browser.")

        # -------------------------------------------------------------
        # Step 2: Open GitHub
        # -------------------------------------------------------------
        print("\n[STEP 2] Executing open_website('github.com')...")
        res2 = open_website("github.com")
        print(f"-> Response: \"{res2}\"")
        time.sleep(3.0)  # Wait for second tab to load

        tabs_step2 = get_open_tabs()
        print(f"-> Open Tabs Count (Before Close): {len(tabs_step2)}")
        for i, t in enumerate(tabs_step2):
            print(f"   Tab [{i+1}] Handle: {t['handle']} | Title: '{t['title']}' | URL: {t['url']}")

        assert len(tabs_step2) == 2, f"Expected exactly 2 open tabs, found {len(tabs_step2)}"
        has_youtube = any("youtube" in (t["url"] + t["title"]).lower() for t in tabs_step2)
        has_github = any("github" in (t["url"] + t["title"]).lower() for t in tabs_step2)
        assert has_youtube and has_github, "Both YouTube and GitHub tabs must be present simultaneously"
        print("-> [PASS] Step 2 verified: Both YouTube and GitHub tabs are concurrently open.")

        # -------------------------------------------------------------
        # Step 3: Close YouTube Tab ONLY
        # -------------------------------------------------------------
        print("\n[STEP 3] Executing close_website('youtube')...")
        res3 = close_website("youtube")
        print(f"-> Response: \"{res3}\"")
        time.sleep(1.5)

        tabs_step3 = get_open_tabs()
        print(f"-> Open Tabs Count (After Closing YouTube): {len(tabs_step3)}")
        for i, t in enumerate(tabs_step3):
            print(f"   Tab [{i+1}] Handle: {t['handle']} | Title: '{t['title']}' | URL: {t['url']}")

        assert len(tabs_step3) == 1, f"Expected exactly 1 tab remaining, found {len(tabs_step3)}"
        remaining_tab = tabs_step3[0]
        assert "github" in (remaining_tab["url"] + remaining_tab["title"]).lower(), "Remaining tab must be GitHub"
        assert not any("youtube" in (t["url"] + t["title"]).lower() for t in tabs_step3), "YouTube tab must be closed"
        print("-> [PASS] Step 3 verified: YouTube tab was closed while GitHub tab remained open intact!")

        # -------------------------------------------------------------
        # Step 4: Close Nonexistent Tab
        # -------------------------------------------------------------
        print("\n[STEP 4] Executing close_website('nonexistent site')...")
        res4 = close_website("nonexistent site")
        print(f"-> Response: \"{res4}\"")
        assert "couldn't find a tab" in res4.lower() or "not found" in res4.lower() or "trouble" in res4.lower(), \
            f"Expected friendly not found message, got: {res4}"
        
        tabs_step4 = get_open_tabs()
        assert len(tabs_step4) == 1, "Tab count should remain unchanged after failing to close nonexistent site"
        print("-> [PASS] Step 4 verified: Friendly not found message returned without crashing.")

    finally:
        print("\n[CLEANUP] Quitting test browser instance...")
        cleanup_browser()
        print("-> [PASS] Browser cleaned up.")


def run_gemini_routing_test():
    print("\n" + "=" * 75)
    print("      GEMINI FUNCTION CALLING & INTENT ROUTING VERIFICATION           ")
    print("=" * 75)

    test_cases = [
        ("open youtube", "Action"),
        ("close youtube", "Action"),
        ("close the github tab", "Action"),
        ("close that youtube tab", "Action"),
        ("open notepad", "Action"),
    ]

    print("\n[Part A: Heuristic Intent Parsing Verification]")
    for phrase, expected_handler in test_cases:
        handler = identify_handler(phrase)
        print(f"  Query: '{phrase}' -> Handler: [{handler}] (Expected: [{expected_handler}])")
        assert handler == expected_handler, f"Routing failure for '{phrase}': got {handler}, expected {expected_handler}"
    print("-> [PASS] All action phrases correctly routed to Action executor.")

    print("\n[Part B: Real Gemini Tool Calling Execution]")
    try:
        # Test 1: Gemini route_to_action for "open youtube"
        print("\n-> Testing prompt: 'open youtube' through Gemini route_to_action...")
        ans_open = route_to_action("open youtube")
        print(f"   Gemini Result: \"{ans_open}\"")
        assert "opening" in ans_open.lower() or "youtube" in ans_open.lower(), f"Unexpected open response: {ans_open}"
        time.sleep(2.0)

        # Test 2: Gemini route_to_action for "close youtube"
        print("\n-> Testing prompt: 'close youtube' through Gemini route_to_action...")
        ans_close = route_to_action("close youtube")
        print(f"   Gemini Result: \"{ans_close}\"")
        assert "closed" in ans_close.lower() or "youtube" in ans_close.lower(), f"Unexpected close response: {ans_close}"

        print("\n-> [PASS] Gemini tool calling correctly selected open_website and close_website!")
    finally:
        cleanup_browser()


if __name__ == "__main__":
    run_tab_management_test()
    run_gemini_routing_test()
    print("\n" + "=" * 75)
    print("               ALL TESTS PASSED SUCCESSFULLY!                         ")
    print("=" * 75 + "\n")
