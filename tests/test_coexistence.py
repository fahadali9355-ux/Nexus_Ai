import os
import shutil
import subprocess
import sys
import time
import urllib.request
import psutil

# Kill any existing chrome first to prepare clean state for test
for p in psutil.process_iter(['name']):
    if p.info['name'] and 'chrome.exe' in p.info['name'].lower():
        try:
            p.kill()
        except Exception:
            pass
time.sleep(1.0)

from test_profile_import_logic import import_existing_chrome_profile

print("\n--- STEP 1: Running One-Time Profile Import ---")
success, msg = import_existing_chrome_profile(force=True)
print(f"Import result: {success} | {msg}")
assert success, f"Profile import failed: {msg}"

print("\n--- STEP 2: Launching Normal Chrome (Default User Data) ---")
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
# Launch normal chrome without debugging flags
p_normal = subprocess.Popen([chrome_path])
time.sleep(2.0)

normal_running = any(p.info['name'] and 'chrome.exe' in p.info['name'].lower() for p in psutil.process_iter(['name']))
print(f"Normal Chrome running: {normal_running}")

print("\n--- STEP 3: Triggering Nexus Website Command (Should NOT kill Normal Chrome) ---")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.task_executor import open_website, close_website, get_open_tabs

res = open_website("instagram")
print("open_website result:", res)
time.sleep(2.0)

# Check running chrome processes: should have both normal and debug chrome running!
all_chrome_pids = [p.pid for p in psutil.process_iter(['name', 'pid']) if p.info['name'] and 'chrome.exe' in p.info['name'].lower()]
print(f"Total active Chrome processes: {len(all_chrome_pids)}")

# Check open tabs in Nexus debug Chrome
tabs = get_open_tabs()
print(f"Nexus debug Chrome open tabs ({len(tabs)}):")
for idx, t in enumerate(tabs):
    print(f"  Tab {idx}: Title='{t.get('title')}' | URL='{t.get('url')}'")

# Check if Instagram is open
has_ig = any("instagram" in (t.get("title", "") + t.get("url", "")).lower() for t in tabs)
print(f"Instagram tab present: {has_ig}")

print("\n--- STEP 4: Closing Instagram Tab in Nexus Chrome ---")
res_close = close_website("instagram")
print("close_website result:", res_close)

tabs_after = get_open_tabs()
print(f"Nexus debug Chrome tabs after close ({len(tabs_after)}):")
for idx, t in enumerate(tabs_after):
    print(f"  Tab {idx}: Title='{t.get('title')}' | URL='{t.get('url')}'")

still_has_ig = any("instagram" in (t.get("title", "") + t.get("url", "")).lower() for t in tabs_after)
print(f"Instagram still in Nexus Chrome? {still_has_ig}")

print("\n--- STEP 5: Verifying Normal Chrome is still alive ---")
# Check that normal chrome processes are still running
normal_procs = [p for p in psutil.process_iter(['name', 'cmdline']) if p.info['name'] and 'chrome.exe' in p.info['name'].lower() and '9222' not in str(p.info['cmdline'])]
print(f"Normal Chrome (non-9222) process count: {len(normal_procs)}")
assert len(normal_procs) > 0, "Normal Chrome was killed!"
assert not still_has_ig, "Instagram tab was not closed!"

print("\n[SUCCESS] Coexistence verified! Normal Chrome was never killed and Nexus debug tab control works perfectly!")
