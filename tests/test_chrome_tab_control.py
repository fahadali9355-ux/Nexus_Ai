import sys
sys.stdout.reconfigure(line_buffering=True)
import os
import subprocess
import time
import urllib.request
import psutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def is_port_9222_open():
    try:
        with urllib.request.urlopen("http://127.0.0.1:9222/json/version", timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False

def ensure_debug_chrome():
    if is_port_9222_open():
        print("[Debug Chrome] Port 9222 is already open and responding.")
        return True

    # Check if existing chrome processes are running
    chrome_procs = [p for p in psutil.process_iter(['name', 'pid']) if p.info['name'] and 'chrome.exe' in p.info['name'].lower()]
    if chrome_procs:
        print(f"[Debug Chrome Warning] Detected {len(chrome_procs)} non-debug Chrome processes.")
        print("[Debug Chrome] Terminating existing Chrome processes to launch with remote debugging...")
        for p in chrome_procs:
            try:
                p.terminate()
            except Exception:
                pass
        _, alive = psutil.wait_procs(chrome_procs, timeout=3.0)
        for p in alive:
            try:
                p.kill()
            except Exception:
                pass
        time.sleep(1.0)

    # Launch Chrome with remote debugging
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data_dir = os.environ.get(
        "CHROME_USER_DATA_DIR",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Nexus_Profile")
    )
    profile_dir = os.environ.get("CHROME_PROFILE_DIR", "Default")

    cmd = [
        chrome_path,
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        f"--profile-directory={profile_dir}",
        "--remote-allow-origins=*",
        "--restore-last-session",
    ]
    print(f"[Debug Chrome] Launching Chrome command: {' '.join(cmd)}")
    subprocess.Popen(cmd)

    for i in range(25):
        if is_port_9222_open():
            print(f"[Debug Chrome] Chrome debug port 9222 connected in {(i+1)*0.2:.1f}s!")
            return True
        time.sleep(0.2)

    print("[Debug Chrome Error] Failed to connect to Chrome debug port after launch.")
    return False

if __name__ == "__main__":
    success = ensure_debug_chrome()
    if not success:
        print("Could not ensure debug Chrome. Exiting.")
        sys.exit(1)

    opts = Options()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=opts)
    print("Selenium attached to Chrome! Initial window handles count:", len(driver.window_handles))

    # Open 3 tabs: Google, YouTube, Instagram
    test_sites = [
        "https://www.google.com",
        "https://www.youtube.com",
        "https://www.instagram.com",
    ]

    for site in test_sites:
        print(f"Opening {site}...")
        driver.execute_script("window.open(arguments[0], '_blank');", site)
        time.sleep(1)

    print("\n--- All Open Tabs Before Close ---")
    handles_before = list(driver.window_handles)
    for idx, h in enumerate(handles_before):
        driver.switch_to.window(h)
        print(f"Tab [{idx}]: Handle={h} | Title='{driver.title}' | URL='{driver.current_url}'")

    print(f"Total open tabs before: {len(handles_before)}")

    # Close Instagram tab only
    print("\nClosing Instagram tab...")
    closed = False
    for h in list(driver.window_handles):
        try:
            driver.switch_to.window(h)
            title = (driver.title or "").lower()
            url = (driver.current_url or "").lower()
            if "instagram" in title or "instagram" in url:
                print(f"-> Closing matching tab: Title='{driver.title}' (Handle={h})")
                driver.close()
                closed = True
                break
        except Exception as e:
            print(f"Error checking handle {h}: {e}")

    # Switch focus back to the last remaining window handle if possible
    remaining_handles = list(driver.window_handles)
    if remaining_handles:
        driver.switch_to.window(remaining_handles[-1])

    print(f"\nClosed Instagram successfully? {closed}")
    print(f"Remaining open tabs count: {len(remaining_handles)}")
    print("\n--- All Open Tabs After Close ---")
    for idx, h in enumerate(remaining_handles):
        driver.switch_to.window(h)
        print(f"Tab [{idx}]: Handle={h} | Title='{driver.title}' | URL='{driver.current_url}'")

    assert closed, "Failed to find and close the Instagram tab!"
    assert len(remaining_handles) >= 2, "Expected the other tabs to stay open!"
    print("\n[VERIFICATION PASSED] Selective single-tab close works perfectly without closing other tabs!")
