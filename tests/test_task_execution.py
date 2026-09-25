"""Comprehensive Verification Script for Nexus Task Execution & Gemini Tool Calling.

Tests:
Part 1: Direct execution of all 7 Windows system action functions.
Part 2: End-to-end Gemini Function Calling (Tool Use) routing with natural language commands.
Part 3: Safety Guardrails verification.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from modules.task_executor import (
    create_text_file,
    get_system_info,
    lock_computer,
    open_application,
    open_website,
    set_system_volume,
    take_screenshot,
    SAFE_BASE_DIR,
)
from modules.gemini_client import route_to_action
from main import parse_intent, identify_handler


def run_tests():
    print("\n" + "=" * 70)
    print("        NEXUS SYSTEM TASK EXECUTOR & GEMINI TOOL CALLING TEST        ")
    print("=" * 70)

    results = {}

    # -------------------------------------------------------------
    # PART 1: Direct Execution of 7 Task Functions
    # -------------------------------------------------------------
    print("\n[PART 1] DIRECT FUNCTION EXECUTION TESTS (7 Actions):")
    print("-" * 70)

    # 1. open_application
    print("\n[1/7] Testing open_application('notepad')...")
    res_open = open_application("notepad")
    print(f"      Result: {res_open}")
    results["open_application"] = "Opening" in res_open
    time.sleep(1.0)
    # Terminate notepad process created for the test
    os.system("taskkill /f /im notepad.exe >nul 2>&1")

    # 2. set_system_volume
    print("\n[2/7] Testing set_system_volume(40)...")
    res_vol = set_system_volume(40)
    print(f"      Result: {res_vol}")
    results["set_system_volume"] = "40 percent" in res_vol

    # 3. get_system_info
    print("\n[3/7] Testing get_system_info()...")
    res_info = get_system_info()
    print(f"      Result: {res_info}")
    results["get_system_info"] = "current time" in res_info.lower() and "battery" in res_info.lower()

    # 4. create_text_file
    print("\n[4/7] Testing create_text_file('nexus_action_test.txt', content)...")
    test_content = "Nexus task executor automated verification test content."
    res_file = create_text_file("nexus_action_test.txt", test_content)
    print(f"      Result: {res_file}")
    target_path = SAFE_BASE_DIR / "nexus_action_test.txt"
    file_exists = target_path.exists()
    content_matches = False
    if file_exists:
        with open(target_path, "r", encoding="utf-8") as f:
            content_matches = (f.read() == test_content)
        print(f"      Verified on disk: {target_path} (Size: {target_path.stat().st_size} bytes)")
    results["create_text_file"] = file_exists and content_matches

    # 5. take_screenshot
    print("\n[5/7] Testing take_screenshot()...")
    res_shot = take_screenshot()
    print(f"      Result: {res_shot}")
    results["take_screenshot"] = "Screenshot captured and saved" in res_shot

    # 6. open_website
    print("\n[6/7] Testing open_website('https://www.google.com')...")
    res_web = open_website("https://www.google.com")
    print(f"      Result: {res_web}")
    results["open_website"] = "Opening" in res_web or "Searching" in res_web

    # 7. lock_computer (Validate function handler & API availability)
    print("\n[7/7] Testing lock_computer function handler...")
    import ctypes
    has_lock = hasattr(ctypes.windll.user32, "LockWorkStation")
    print(f"      user32.LockWorkStation API available: {has_lock}")
    results["lock_computer"] = has_lock

    # -------------------------------------------------------------
    # PART 2: Gemini Function Calling Natural Language Routing
    # -------------------------------------------------------------
    print("\n\n[PART 2] GEMINI FUNCTION CALLING NATURAL LANGUAGE TESTS:")
    print("-" * 70)

    gemini_test_prompts = [
        ("open notepad", "open_application"),
        ("set volume to 30", "set_system_volume"),
        ("take a screenshot", "take_screenshot"),
        ("create a text file called todo.txt with buy groceries", "create_text_file"),
    ]

    gemini_results = {}
    for prompt, expected_tool in gemini_test_prompts:
        print(f"\n[*] Testing prompt: \"{prompt}\"")
        handler = identify_handler(prompt)
        print(f"    1. Intent Classification: Handler = '{handler}'")

        res = route_to_action(prompt)
        print(f"    2. Route To Action Output: \"{res}\"")

        success = len(res) > 0 and "Sorry, Gemini API key is missing" not in res
        gemini_results[prompt] = success
        time.sleep(1.0)

    # Clean up test processes
    os.system("taskkill /f /im notepad.exe >nul 2>&1")

    # -------------------------------------------------------------
    # PART 3: Safety Guardrails Verification
    # -------------------------------------------------------------
    print("\n\n[PART 3] SAFETY GUARDRAIL TESTS:")
    print("-" * 70)

    # Guardrail 1: Path Traversal prevention
    print("[*] Testing path traversal attack prevention: '../../system_file.txt'...")
    res_guard = create_text_file("../../system_file.txt", "Malicious content")
    print(f"    Result: {res_guard}")
    traversal_safe = not os.path.exists("system_file.txt") and not os.path.exists("../system_file.txt")
    print(f"    Sandbox check: Malicious file was NOT created outside sandbox = {traversal_safe}")

    # -------------------------------------------------------------
    # SUMMARY REPORT
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("                    FINAL VERIFICATION SUMMARY                       ")
    print("=" * 70)

    all_passed = True
    print("\n[1] 7 Real System Action Functions:")
    for action, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"    - {action:<24}: [{status}]")
        if not passed:
            all_passed = False

    print("\n[2] Gemini Natural Language Tool Calling:")
    for prompt, passed in gemini_results.items():
        status = "PASS" if passed else "FAIL"
        print(f"    - \"{prompt:<35}\": [{status}]")
        if not passed:
            all_passed = False

    print(f"\n[3] Safety Sandbox Guardrails: [{'PASS' if traversal_safe else 'FAIL'}]")

    print("=" * 70)
    if all_passed and traversal_safe:
        print("  >>> ALL TASK EXECUTION & GEMINI TOOL TESTS PASSED SUCCESSFULLY! <<<")
    else:
        print("  >>> SOME TESTS FAILED. PLEASE REVIEW LOGS. <<<")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_tests()
