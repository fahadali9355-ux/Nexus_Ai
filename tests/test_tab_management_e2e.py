import os
import sys
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
from modules.task_executor import open_website, close_website, get_open_tabs, cleanup_browser

def test_full_tab_lifecycle():
    print("\n========================================================")
    print("      Nexus Browser Remote Debugging & Tab Lifecycle Test")
    print("========================================================")

    # 1. Open Google
    print("\n[STEP 1] Opening Google...")
    res1 = open_website("google")
    print("Result:", res1)
    time.sleep(1.0)

    # 2. Open YouTube
    print("\n[STEP 2] Opening YouTube...")
    res2 = open_website("youtube")
    print("Result:", res2)
    time.sleep(1.0)

    # 3. Open Instagram
    print("\n[STEP 3] Opening Instagram...")
    res3 = open_website("instagram")
    print("Result:", res3)
    time.sleep(1.0)

    # 4. Inspect open tabs
    tabs_before = get_open_tabs()
    print(f"\n[STEP 4] Open tabs count before close: {len(tabs_before)}")
    for idx, t in enumerate(tabs_before):
        print(f"  Tab {idx}: Title='{t.get('title')}' | URL='{t.get('url')}'")

    has_instagram = any("instagram" in (t.get("title", "") + t.get("url", "")).lower() for t in tabs_before)
    has_youtube = any("youtube" in (t.get("title", "") + t.get("url", "")).lower() for t in tabs_before)
    has_google = any("google" in (t.get("title", "") + t.get("url", "")).lower() for t in tabs_before)

    print(f"Contains Instagram: {has_instagram}, YouTube: {has_youtube}, Google: {has_google}")
    assert has_instagram, "Instagram tab was not opened!"
    assert has_youtube, "YouTube tab was not opened!"

    # 5. Close ONLY the Instagram tab
    print("\n[STEP 5] Calling close_website('instagram')...")
    res_close = close_website("instagram")
    print("Result:", res_close)
    time.sleep(1.0)

    # 6. Verify tabs after closing Instagram
    tabs_after = get_open_tabs()
    print(f"\n[STEP 6] Open tabs count after close: {len(tabs_after)}")
    for idx, t in enumerate(tabs_after):
        print(f"  Tab {idx}: Title='{t.get('title')}' | URL='{t.get('url')}'")

    still_has_instagram = any("instagram" in (t.get("title", "") + t.get("url", "")).lower() for t in tabs_after)
    still_has_youtube = any("youtube" in (t.get("title", "") + t.get("url", "")).lower() for t in tabs_after)
    still_has_google = any("google" in (t.get("title", "") + t.get("url", "")).lower() for t in tabs_after)

    print(f"Instagram still open? {still_has_instagram} (Should be False)")
    print(f"YouTube still open? {still_has_youtube} (Should be True)")
    print(f"Google still open? {still_has_google} (Should be True)")

    assert not still_has_instagram, "Instagram tab should have been closed!"
    assert still_has_youtube, "YouTube tab MUST remain open!"
    assert "Closed the tab" in res_close or "Closed" in res_close, f"Unexpected response: {res_close}"

    # 7. Non-existent tab test
    print("\n[STEP 7] Testing non-existent tab close...")
    res_nonexistent = close_website("some_random_nonexistent_tab_123")
    print("Result:", res_nonexistent)
    assert "couldn't find an open tab" in res_nonexistent.lower() or "not found" in res_nonexistent.lower()

    # 8. Cleanup
    print("\n[STEP 8] Testing browser cleanup...")
    cleanup_browser()
    print("Cleanup completed successfully.")

    print("\n========================================================")
    print("      [TEST PASSED] All single-tab operations succeeded!")
    print("========================================================\n")

if __name__ == "__main__":
    test_full_tab_lifecycle()
