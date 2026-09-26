"""Task Executor Module for Nexus Voice Assistant.

Provides Windows-compatible real system task execution capabilities:
1. open_application(app_name)
2. set_system_volume(level)
3. lock_computer()
4. take_screenshot()
5. open_website(url_or_search_term)
6. get_system_info()
7. create_text_file(filename, content)
"""

import atexit
import ctypes
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request
import webbrowser

from modules.document_generator import (
    create_assignment_document,
    create_docx,
    create_pdf,
    create_pptx,
    open_generated_file,
)


# Designated safe folder for Nexus user-generated files and screenshots
SAFE_BASE_DIR = Path.home() / "Documents" / "Nexus"

# Known application executable / launch mappings for Windows
KNOWN_APPS: Dict[str, str] = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "files": "explorer.exe",
    "this pc": "explorer.exe",
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "edge": "start msedge",
    "msedge": "start msedge",
    "microsoft edge": "start msedge",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "settings": "start ms-settings:",
    "control panel": "control.exe",
    "wordpad": "write.exe",
}

# Known web services and social platforms with their canonical URLs
KNOWN_SERVICES: Dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "github": "https://www.github.com",
    "google": "https://www.google.com",
    "reddit": "https://www.reddit.com",
    "twitter": "https://www.twitter.com",
    "x": "https://www.x.com",
    "wikipedia": "https://www.wikipedia.org",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chatgpt.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "whatsapp": "https://web.whatsapp.com",
    "linkedin": "https://www.linkedin.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "amazon": "https://www.amazon.com",
    "twitch": "https://www.twitch.tv",
    "pinterest": "https://www.pinterest.com",
    "tiktok": "https://www.tiktok.com",
}


def _ensure_safe_directory() -> Path:
    """Ensures the designated safe directory exists and returns its Path."""
    try:
        SAFE_BASE_DIR.mkdir(parents=True, exist_ok=True)
        return SAFE_BASE_DIR
    except Exception:
        fallback_dir = Path("safe_storage").resolve()
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir


def open_application(app_name: str) -> str:
    """Opens common Windows desktop applications safely using subprocess or os.startfile.

    Args:
        app_name (str): Name of the application (e.g., 'notepad', 'calculator', 'chrome', 'explorer').

    Returns:
        str: TTS-friendly outcome description.
    """
    if not app_name or not str(app_name).strip():
        return "Please specify the application you would like to open."

    clean_name = str(app_name).strip().lower()

    try:
        target = KNOWN_APPS.get(clean_name)
        if target:
            if target.startswith("start "):
                subprocess.Popen(target, shell=True)
            else:
                subprocess.Popen([target])
            return f"Opening {app_name.capitalize()}."
        else:
            # Fallback: try opening with startfile or shell start
            try:
                os.startfile(clean_name)
                return f"Opening {app_name}."
            except Exception:
                subprocess.Popen(["cmd.exe", "/c", "start", clean_name], shell=True)
                return f"Attempting to launch {app_name}."
    except Exception as e:
        return f"Sorry, I could not open {app_name}. {str(e)}"


def set_system_volume(level: int) -> str:
    """Sets the system master volume (0-100) using pycaw.

    Args:
        level (int): Target volume percentage from 0 to 100.

    Returns:
        str: TTS-friendly confirmation message.
    """
    try:
        vol_level = max(0, min(100, int(level)))

        # Initialize COM library for the active thread if not already initialized
        try:
            import comtypes
            comtypes.CoInitialize()
        except Exception:
            pass

        from typing import Any
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL

        speakers: Any = AudioUtilities.GetSpeakers()
        if hasattr(speakers, "EndpointVolume") and speakers.EndpointVolume is not None:
            volume: Any = speakers.EndpointVolume
        elif hasattr(speakers, "Activate"):
            interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
        elif hasattr(speakers, "_dev") and hasattr(speakers._dev, "Activate"):
            interface = speakers._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
        else:
            raise RuntimeError("Unable to access audio endpoint volume interface.")

        volume.SetMasterVolumeLevelScalar(vol_level / 100.0, None)
        return f"System volume set to {vol_level} percent."
    except Exception as e:
        return f"Sorry, could not adjust system volume: {str(e)}"


def lock_computer() -> str:
    """Locks the Windows computer workstation session.

    Returns:
        str: TTS-friendly confirmation message.
    """
    try:
        res = ctypes.windll.user32.LockWorkStation()
        if res != 0:
            return "Locking the computer."
        return "Could not lock the workstation."
    except Exception as e:
        return f"Error locking computer: {str(e)}"


def take_screenshot() -> str:
    """Captures a full desktop screenshot and saves it with a timestamped filename in Documents/Nexus.

    Returns:
        str: TTS-friendly confirmation message including the saved file path.
    """
    try:
        from PIL import Image

        safe_dir = _ensure_safe_directory()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = safe_dir / filename

        # Primary capture method using Windows GDI via ctypes (resilient across sessions)
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)

        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
        gdi32.SelectObject(hdc_mem, hbm)

        # Copy screen to memory DC (SRCCOPY = 0x00CC0020)
        gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", ctypes.c_uint32),
                ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16),
                ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32),
                ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32),
                ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32),
            ]

        bih = BITMAPINFOHEADER()
        bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bih.biWidth = w
        bih.biHeight = -h  # top-down bitmap
        bih.biPlanes = 1
        bih.biBitCount = 32
        bih.biCompression = 0

        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf, ctypes.byref(bih), 0)

        # Cleanup GDI handles
        gdi32.DeleteObject(hbm)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)

        img = Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1)
        img.convert("RGB").save(str(filepath))

        return f"Screenshot captured and saved to your Nexus Documents folder as {filename}."
    except Exception as e:
        return f"Sorry, could not capture screenshot: {str(e)}"

# Module-level persistent Selenium driver lock and instance
_driver: Optional[Any] = None
_driver_lock = threading.Lock()
CHROME_DEBUG_PORT = 9222


def _find_chrome_executable() -> Optional[str]:
    """Locates the Google Chrome executable on the host system."""
    candidates = [
        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        shutil.which("chrome.exe"),
        shutil.which("chrome"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return os.path.abspath(c)
    return None


def _is_debug_port_open(host: str = "127.0.0.1", port: int = CHROME_DEBUG_PORT, timeout: float = 0.5) -> bool:
    """Checks whether Chrome is running and responding on the remote debugging port."""
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/json/version", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def is_chrome_running() -> bool:
    """Checks if any chrome.exe processes are currently running on the system."""
    try:
        import psutil

        for p in psutil.process_iter(["name"]):
            if p.info["name"] and "chrome.exe" in p.info["name"].lower():
                return True
    except Exception:
        pass
    return False


def import_existing_chrome_profile(force: bool = False) -> Tuple[bool, str]:
    """Imports login sessions, cookies, and preferences from the default Chrome profile into Nexus_Profile.

    Note:
        Chrome encrypts cookies and passwords using an encrypted key in 'Local State' via Windows DPAPI.
        Copying both 'Local State' and the 'Default' profile database files allows Nexus_Profile to
        access the user's existing logged-in accounts (e.g. Instagram, YouTube, GitHub) without re-logging in.
        Chrome MUST be fully closed during this operation to prevent locked database errors.

    Args:
        force (bool): If True, overwrites existing files in Nexus_Profile even if already present.

    Returns:
        Tuple[bool, str]: (Success boolean, Status/Outcome message).
    """
    real_user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    nexus_user_data = os.environ.get(
        "CHROME_USER_DATA_DIR",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Nexus_Profile"),
    )

    if not os.path.exists(real_user_data):
        return False, f"Source Chrome profile directory not found at: {real_user_data}"

    target_cookies = os.path.join(nexus_user_data, "Default", "Network", "Cookies")
    target_local_state = os.path.join(nexus_user_data, "Local State")

    # If not forced and already imported, skip
    if not force and os.path.exists(target_cookies) and os.path.exists(target_local_state):
        return True, "Nexus_Profile already has imported login data. Pass force=True to re-import."

    # Check if Chrome is running
    if is_chrome_running():
        return False, (
            "Chrome is currently running. Chrome locks its login and cookie databases while open. "
            "Please close all Chrome windows (including any background instances) before running the import."
        )

    try:
        os.makedirs(os.path.join(nexus_user_data, "Default", "Network"), exist_ok=True)

        # 1. Copy Local State (essential for DPAPI master key decryption)
        src_local_state = os.path.join(real_user_data, "Local State")
        if os.path.exists(src_local_state):
            shutil.copy2(src_local_state, target_local_state)
            print(f"[Profile Import] Copied Local State -> {target_local_state}")

        # 2. Copy Default profile files (Cookies, Login Data, Preferences, Bookmarks, History)
        src_default = os.path.join(real_user_data, "Default")
        tgt_default = os.path.join(nexus_user_data, "Default")

        files_to_copy = [
            ("Preferences", "Preferences"),
            ("Secure Preferences", "Secure Preferences"),
            ("Login Data", "Login Data"),
            ("Login Data-journal", "Login Data-journal"),
            ("Web Data", "Web Data"),
            ("Web Data-journal", "Web Data-journal"),
            ("Bookmarks", "Bookmarks"),
            ("History", "History"),
            ("Favicons", "Favicons"),
            ("Cookies", "Cookies"),
            (os.path.join("Network", "Cookies"), os.path.join("Network", "Cookies")),
            (os.path.join("Network", "Cookies-journal"), os.path.join("Network", "Cookies-journal")),
            (os.path.join("Network", "Network Persistent State"), os.path.join("Network", "Network Persistent State")),
            (os.path.join("Network", "TransportSecurity"), os.path.join("Network", "TransportSecurity")),
            (os.path.join("Network", "Trust Tokens"), os.path.join("Network", "Trust Tokens")),
        ]

        copied_count = 0
        for src_rel, tgt_rel in files_to_copy:
            src_file = os.path.join(src_default, src_rel)
            tgt_file = os.path.join(tgt_default, tgt_rel)
            if os.path.exists(src_file):
                os.makedirs(os.path.dirname(tgt_file), exist_ok=True)
                shutil.copy2(src_file, tgt_file)
                copied_count += 1

        print(f"[Profile Import] Successfully imported {copied_count} profile files into Nexus_Profile.")
        return True, f"Successfully imported Chrome profile ({copied_count} files) into Nexus_Profile."
    except Exception as e:
        print(f"[Profile Import Error] Failed to import Chrome profile: {e}")
        return False, f"Failed to import Chrome profile: {e}"


def _ensure_debug_chrome() -> bool:
    """Ensures Chrome is running with remote debugging enabled (--remote-debugging-port=9222).

    Uses a dedicated user-data-dir ('Nexus_Profile') allowing Nexus to run alongside
    the user's normal Chrome windows without terminating or interfering with them.
    """
    if _is_debug_port_open():
        return True

    chrome_path = _find_chrome_executable()
    if not chrome_path:
        print("[Chrome Setup Error] Google Chrome executable not found on system.")
        return False

    # Determine user data directory (defaults to Nexus_Profile to satisfy Chromium security requirement)
    user_data_dir = os.environ.get(
        "CHROME_USER_DATA_DIR",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Nexus_Profile"),
    )
    profile_dir = os.environ.get("CHROME_PROFILE_DIR", "Default")

    cmd = [
        chrome_path,
        f"--remote-debugging-port={CHROME_DEBUG_PORT}",
        f"--user-data-dir={user_data_dir}",
        f"--profile-directory={profile_dir}",
        "--remote-allow-origins=*",
        "--restore-last-session",
    ]

    try:
        print(f"[Chrome Setup] Launching debug-enabled Chrome: {' '.join(cmd)}")
        subprocess.Popen(cmd)
    except Exception as launch_err:
        print(f"[Chrome Setup Error] Failed to launch Chrome: {launch_err}")
        return False

    # Poll until remote debugging port is active (up to 5 seconds)
    for _ in range(25):
        if _is_debug_port_open():
            print(f"[Chrome Setup] Chrome remote debugging connected successfully on port {CHROME_DEBUG_PORT}.")
            return True
        time.sleep(0.2)

    print(f"[Chrome Setup Error] Timed out waiting for Chrome debug port {CHROME_DEBUG_PORT}.")
    return False


def _cdp_get_tabs() -> List[Dict[str, Any]]:
    """Retrieves metadata of all open browser tabs via Chrome DevTools Protocol HTTP API."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{CHROME_DEBUG_PORT}/json/list", timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
            return [t for t in data if t.get("type") == "page"]
    except Exception as e:
        print(f"[Browser CDP] Error getting tab list: {e}")
        return []


def _cdp_open_tab(url: str) -> bool:
    """Opens a new tab navigating to target URL via Chrome DevTools Protocol HTTP API."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{CHROME_DEBUG_PORT}/json/new?{url}", method="PUT")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Browser CDP] Error opening tab '{url}': {e}")
        return False


def _cdp_close_tab(target_id: str) -> bool:
    """Closes a specific tab by target ID via Chrome DevTools Protocol HTTP API."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{CHROME_DEBUG_PORT}/json/close/{target_id}", method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Browser CDP] Error closing tab ID '{target_id}': {e}")
        return False


def _cdp_activate_tab(target_id: str) -> bool:
    """Brings a specific tab into active focus via Chrome DevTools Protocol HTTP API."""
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{CHROME_DEBUG_PORT}/json/activate/{target_id}", method="GET")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[Browser CDP] Error activating tab ID '{target_id}': {e}")
        return False


def _get_driver() -> Optional[Any]:
    """Retrieves or initializes Selenium WebDriver attached to the running debug-enabled Chrome instance.

    Uses options.add_experimental_option('debuggerAddress', '127.0.0.1:9222') so all Selenium
    actions control the user's active Chrome instance without spawning separate processes.
    """
    global _driver
    with _driver_lock:
        if _driver is not None:
            try:
                _ = _driver.window_handles
                return _driver
            except Exception:
                try:
                    _driver.quit()
                except Exception:
                    pass
                _driver = None

        if not _ensure_debug_chrome():
            return None

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            options = Options()
            options.page_load_strategy = "none"
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{CHROME_DEBUG_PORT}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--log-level=3")

            service = Service(ChromeDriverManager().install())
            _driver = webdriver.Chrome(service=service, options=options)
            print("[Browser Automation] Selenium attached to debug-enabled Chrome instance.")
            return _driver
        except Exception as driver_err:
            print(f"[Browser Automation Warning] Failed to attach Selenium WebDriver: {driver_err}")
            _driver = None
            return None


def cleanup_browser() -> None:
    """Disconnects the persistent Selenium WebDriver session without closing the user's Chrome windows."""
    global _driver
    with _driver_lock:
        if _driver is not None:
            try:
                print("[Browser Automation] Disconnecting Selenium WebDriver session...")
                _driver.quit()
            except Exception as quit_err:
                print(f"[Browser Automation Warning] Note during disconnect: {quit_err}")
            finally:
                _driver = None


# Register cleanup with Python atexit handler
atexit.register(cleanup_browser)


def open_website(url_or_search_term: str) -> str:
    """Opens a website URL or search query as a new tab in the debug-enabled Chrome instance.

    Ensures Chrome is running with remote debugging enabled so all opened tabs can later be
    selectively targeted and closed individually without affecting other open tabs.

    Args:
        url_or_search_term (str): Web address or search keywords.

    Returns:
        str: TTS-friendly confirmation message.
    """
    if not url_or_search_term or not str(url_or_search_term).strip():
        return "Please specify a URL or search query to open."

    raw_target = str(url_or_search_term).strip()
    target_lower = raw_target.lower()

    # Determine target URL
    if target_lower.startswith("http://") or target_lower.startswith("https://"):
        target_url = raw_target
    elif "." in raw_target and " " not in raw_target:
        target_url = f"https://{raw_target}"
    else:
        # Check if known direct service without TLD (e.g. 'instagram', 'youtube', 'github', 'reddit')
        if target_lower in KNOWN_SERVICES:
            target_url = KNOWN_SERVICES[target_lower]
        else:
            query_enc = urllib.parse.quote_plus(raw_target)
            target_url = f"https://www.google.com/search?q={query_enc}"

    # Ensure debug-enabled Chrome is running
    chrome_ready = _ensure_debug_chrome()
    if not chrome_ready:
        # Fallback to standard browser launch if Chrome could not be initialized
        try:
            webbrowser.open(target_url)
            return f"Opening {raw_target} in your browser."
        except Exception as wb_err:
            return f"Sorry, could not open website: {wb_err}"

    # Primary method: Instant DevTools Protocol tab creation (0.02s latency, non-blocking)
    opened = _cdp_open_tab(target_url)
    if not opened:
        # Fallback to Selenium attached driver
        driver = _get_driver()
        if driver is not None:
            try:
                with _driver_lock:
                    if driver.window_handles:
                        driver.switch_to.window(driver.window_handles[-1])
                    driver.execute_script("window.open(arguments[0], '_blank');", target_url)
                    opened = True
            except Exception as sel_err:
                print(f"[Browser Automation Error] Selenium tab open fallback failed: {sel_err}")

    if opened:
        return f"Opening {raw_target} in your browser."
    else:
        return f"Sorry, could not open {raw_target} in your browser."


def close_website(identifier: str) -> str:
    """Selectively closes ONLY the specific browser tab matching the target website name or keyword.

    Leaves all other open tabs completely untouched and alive.

    Args:
        identifier (str): Website name, domain, or keyword (e.g. 'instagram', 'youtube', 'github').

    Returns:
        str: TTS-friendly confirmation or not-found message.
    """
    if not identifier or not str(identifier).strip():
        return "Please specify the website tab you would like to close."

    clean_target = str(identifier).strip().lower()
    # Normalize common conversational suffixes (e.g. 'instagram tab' -> 'instagram')
    for suffix in [" tab", " website", " webpage", " page", " window"]:
        if clean_target.endswith(suffix):
            clean_target = clean_target[: -len(suffix)].strip()

    if not clean_target:
        clean_target = str(identifier).strip().lower()

    # Ensure Chrome debug port is active
    if not _is_debug_port_open():
        if not _ensure_debug_chrome():
            return f"I couldn't find an open tab for '{identifier}'."

    # Query all active tabs via DevTools Protocol
    tabs = _cdp_get_tabs()
    matching_tabs: List[Dict[str, Any]] = []

    for t in tabs:
        title = (t.get("title") or "").lower()
        url = (t.get("url") or "").lower()
        if clean_target in title or clean_target in url:
            matching_tabs.append(t)

    # If CDP found matching tabs, close only the matching tab(s)
    if matching_tabs:
        closed_count = 0
        for t in matching_tabs:
            tid = t.get("id")
            if tid and _cdp_close_tab(tid):
                closed_count += 1

        # Activate the most recent remaining tab so the window stays active
        remaining = _cdp_get_tabs()
        if remaining:
            active_id = remaining[0].get("id")
            if active_id:
                _cdp_activate_tab(active_id)

        if closed_count == 1:
            return f"Closed the tab for '{identifier}'."
        elif closed_count > 1:
            return f"Closed {closed_count} tabs matching '{identifier}'."

    # Secondary fallback via attached Selenium driver
    driver = _get_driver()
    if driver is not None:
        try:
            with _driver_lock:
                closed_count = 0
                for h in list(driver.window_handles):
                    try:
                        driver.switch_to.window(h)
                        title = (driver.title or "").lower()
                        url = (driver.current_url or "").lower()
                        if clean_target in title or clean_target in url:
                            driver.close()
                            closed_count += 1
                            break  # Close most relevant matching tab
                    except Exception:
                        pass

                # Restore focus to a remaining window handle
                if driver.window_handles:
                    driver.switch_to.window(driver.window_handles[-1])

                if closed_count > 0:
                    return f"Closed the tab for '{identifier}'."
        except Exception as sel_err:
            print(f"[Browser Automation Error] Selenium tab close error: {sel_err}")

    return f"I couldn't find an open tab for '{identifier}'."


def get_open_tabs() -> List[Dict[str, str]]:
    """Returns a list of metadata for all currently open tabs in the automated browser session.

    Useful for diagnostics and automated verification.

    Returns:
        List[Dict[str, str]]: List of dictionaries containing handle/id, title, and current URL.
    """
    tabs = _cdp_get_tabs()
    if tabs:
        return [
            {
                "handle": t.get("id", ""),
                "title": t.get("title", ""),
                "url": t.get("url", ""),
            }
            for t in tabs
        ]

    driver = _get_driver()
    if driver is None:
        return []

    tabs_info: List[Dict[str, str]] = []
    try:
        with _driver_lock:
            current_handle = driver.current_window_handle
            for h in driver.window_handles:
                try:
                    driver.switch_to.window(h)
                    tabs_info.append(
                        {
                            "handle": h,
                            "title": driver.title,
                            "url": driver.current_url,
                        }
                    )
                except Exception:
                    pass
            if current_handle in driver.window_handles:
                driver.switch_to.window(current_handle)
    except Exception as e:
        print(f"[Browser Automation] Error inspecting open tabs: {e}")

    return tabs_info


def get_system_info() -> str:
    """Returns current system battery %, time, and date.

    Returns:
        str: TTS-friendly description of system status.
    """
    try:
        import psutil

        now = datetime.now()
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")

        battery = psutil.sensors_battery()
        if battery is not None:
            percent = int(battery.percent)
            plugged = "plugged in" if battery.power_plugged else "running on battery"
            battery_str = f"battery is at {percent} percent ({plugged})"
        else:
            battery_str = "system is running on AC power"

        return f"The current time is {time_str} on {date_str}. Your {battery_str}."
    except Exception as e:
        return f"Error retrieving system information: {str(e)}"


def create_text_file(filename: str, content: str) -> str:
    """Creates a text file safely within the designated Documents/Nexus directory.

    Strict guardrails:
    - Path traversal protection (strips directory paths, restricts strictly to Documents/Nexus).
    - Appends .txt extension if omitted.

    Args:
        filename (str): Name of the file (e.g. notes.txt).
        content (str): Text content to write.

    Returns:
        str: TTS-friendly confirmation message.
    """
    try:
        safe_dir = _ensure_safe_directory()

        # Sanitize filename - prevent path traversal attacks (e.g. ../../windows)
        clean_base = os.path.basename(str(filename).strip())
        if not clean_base:
            clean_base = "note.txt"
        if not os.path.splitext(clean_base)[1]:
            clean_base += ".txt"

        target_path = (safe_dir / clean_base).resolve()

        # Enforce sandbox guardrail: Target file must resolve strictly inside safe_dir
        if not str(target_path).startswith(str(safe_dir.resolve())):
            return "Security restriction: Cannot create files outside the Documents/Nexus folder."

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(str(content))

        return f"Created text file {clean_base} in your Nexus Documents folder."
    except Exception as e:
        return f"Sorry, could not create text file: {str(e)}"
