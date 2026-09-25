"""Task Executor Module for Aetheris Voice Assistant.

Provides Windows-compatible real system task execution capabilities:
1. open_application(app_name)
2. set_system_volume(level)
3. lock_computer()
4. take_screenshot()
5. open_website(url_or_search_term)
6. get_system_info()
7. create_text_file(filename, content)
"""

import ctypes
from datetime import datetime
import os
from pathlib import Path
import subprocess
import urllib.parse
import webbrowser
from typing import Optional


# Designated safe folder for Aetheris user-generated files and screenshots
SAFE_BASE_DIR = Path.home() / "Documents" / "Aetheris"


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

    # Known application mappings for Windows
    app_map = {
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

    try:
        target = app_map.get(clean_name)
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
    """Captures a full desktop screenshot and saves it with a timestamped filename in Documents/Aetheris.

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

        return f"Screenshot captured and saved to your Aetheris Documents folder as {filename}."
    except Exception as e:
        return f"Sorry, could not capture screenshot: {str(e)}"


import atexit
import threading
from typing import Any, Dict, List, Optional

# Module-level persistent Selenium driver and tracked tabs mapping
_driver: Optional[Any] = None
_driver_lock = threading.Lock()
_tracked_tabs: Dict[str, str] = {}  # {friendly_key: window_handle}


def _get_driver() -> Optional[Any]:
    """Retrieves or lazily initializes the persistent Selenium Chrome WebDriver instance.

    Uses webdriver-manager for automatic ChromeDriver binary management.
    Thread-safe and verifies active browser session liveness.
    """
    global _driver
    with _driver_lock:
        if _driver is not None:
            try:
                # Check if the driver session is still alive
                _ = _driver.window_handles
                return _driver
            except Exception:
                # Session expired or user manually closed Chrome window
                try:
                    _driver.quit()
                except Exception:
                    pass
                _driver = None
                _tracked_tabs.clear()

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            options = Options()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--log-level=3")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            # Auto-install/match compatible ChromeDriver binary
            service = Service(ChromeDriverManager().install())
            _driver = webdriver.Chrome(service=service, options=options)
            print("[Browser Automation] Persistent Selenium Chrome WebDriver initialized.")
            return _driver
        except Exception as driver_err:
            print(f"[Browser Automation Warning] Failed to initialize Selenium WebDriver: {driver_err}")
            _driver = None
            return None


def cleanup_browser() -> None:
    """Gracefully quits the persistent Selenium browser instance and frees resources."""
    global _driver
    with _driver_lock:
        if _driver is not None:
            try:
                print("[Browser Automation] Closing persistent Selenium WebDriver...")
                _driver.quit()
            except Exception as quit_err:
                print(f"[Browser Automation Warning] Error quitting WebDriver: {quit_err}")
            finally:
                _driver = None
                _tracked_tabs.clear()


# Register cleanup with Python atexit handler
atexit.register(cleanup_browser)


def _extract_friendly_key(url_or_term: str) -> str:
    """Extracts a normalized, friendly key from a URL or search query for tab tracking."""
    cleaned = str(url_or_term).strip().lower()
    # Remove protocol prefix
    if cleaned.startswith("http://"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("https://"):
        cleaned = cleaned[8:]
    # Remove leading 'www.'
    if cleaned.startswith("www."):
        cleaned = cleaned[4:]
    # Split query parameters or path
    cleaned = cleaned.split("/")[0].split("?")[0]
    # If domain contains extensions, extract base name (e.g. 'youtube.com' -> 'youtube')
    parts = cleaned.split(".")
    if len(parts) > 1 and parts[0]:
        return parts[0]
    return cleaned


def open_website(url_or_search_term: str) -> str:
    """Opens a website URL or search term in a new tab of the persistent Selenium browser.

    Tracks the window handle under friendly identifiers for targeted tab closing.
    Falls back gracefully to the standard default browser if Selenium is unavailable.

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
        # Check if known direct service without TLD (e.g. 'youtube', 'github', 'reddit')
        known_services = {
            "youtube": "https://www.youtube.com",
            "github": "https://www.github.com",
            "google": "https://www.google.com",
            "reddit": "https://www.reddit.com",
            "twitter": "https://www.twitter.com",
            "x": "https://www.x.com",
            "wikipedia": "https://www.wikipedia.org",
            "gmail": "https://mail.google.com",
            "chatgpt": "https://chatgpt.com",
        }
        if target_lower in known_services:
            target_url = known_services[target_lower]
        else:
            query_enc = urllib.parse.quote_plus(raw_target)
            target_url = f"https://www.google.com/search?q={query_enc}"

    driver = _get_driver()
    if driver is None:
        # Fallback to standard system browser
        try:
            webbrowser.open(target_url)
            return f"Opening {raw_target} in your default browser."
        except Exception as wb_err:
            return f"Sorry, could not open web link: {wb_err}"

    # Selenium browser automation
    try:
        with _driver_lock:
            handles = driver.window_handles
            if len(handles) == 1 and driver.current_url in ("data:,", "about:blank", ""):
                # Reuse the initial default blank tab
                driver.get(target_url)
                current_handle = driver.current_window_handle
            else:
                # Open a new tab in the existing browser window
                driver.switch_to.new_window("tab")
                driver.get(target_url)
                current_handle = driver.current_window_handle

            # Store friendly key and raw target mappings
            friendly_key = _extract_friendly_key(raw_target)
            _tracked_tabs[friendly_key] = current_handle
            _tracked_tabs[target_lower] = current_handle

            return f"Opening {raw_target} in a new browser tab."
    except Exception as sel_err:
        print(f"[Browser Automation Error] Selenium navigation failed: {sel_err}. Falling back to default browser...")
        try:
            webbrowser.open(target_url)
            return f"Opening {raw_target} in your default browser."
        except Exception:
            return f"Sorry, could not open website: {sel_err}"


def close_website(identifier: str) -> str:
    """Closes a specific website tab in the persistent Selenium browser by name or keyword.

    Searches tracked tabs first, then checks active tab titles/URLs across the session.
    Only closes the matched tab, leaving other tabs and the browser active.

    Args:
        identifier (str): Website name, domain, or keyword (e.g. 'youtube', 'github', 'google').

    Returns:
        str: TTS-friendly confirmation message.
    """
    if not identifier or not str(identifier).strip():
        return "Please specify the website tab you would like to close."

    clean_id = str(identifier).strip().lower()
    # Normalize common conversational suffixes (e.g. 'youtube tab' -> 'youtube')
    for suffix in [" tab", " website", " webpage", " page"]:
        if clean_id.endswith(suffix):
            clean_id = clean_id[: -len(suffix)].strip()

    driver = _get_driver()
    if driver is None:
        return f"I couldn't find a tab for '{identifier}' that's currently open."

    try:
        with _driver_lock:
            all_handles = driver.window_handles
            if not all_handles:
                _tracked_tabs.clear()
                return f"I couldn't find a tab for '{identifier}' that's currently open."

            # Clean stale handles from tracked dictionary
            stale_keys = [k for k, h in _tracked_tabs.items() if h not in all_handles]
            for k in stale_keys:
                _tracked_tabs.pop(k, None)

            target_handle: Optional[str] = None
            target_name = identifier

            # Step 1: Check tracked tabs dictionary (exact or substring match)
            if clean_id in _tracked_tabs:
                target_handle = _tracked_tabs[clean_id]
                target_name = clean_id
            else:
                for tracked_key, handle in _tracked_tabs.items():
                    if clean_id in tracked_key or tracked_key in clean_id:
                        target_handle = handle
                        target_name = tracked_key
                        break

            # Step 2: Fallback - Inspect all open tabs in current session by Title and URL
            if target_handle is None:
                current_active = driver.current_window_handle
                for h in all_handles:
                    try:
                        driver.switch_to.window(h)
                        title = (driver.title or "").lower()
                        url = (driver.current_url or "").lower()
                        if clean_id in title or clean_id in url:
                            target_handle = h
                            target_name = driver.title or identifier
                            break
                    except Exception:
                        continue
                # Restore active window if no match was found
                if target_handle is None and current_active in all_handles:
                    try:
                        driver.switch_to.window(current_active)
                    except Exception:
                        pass

            # Step 3: If tab was found, close ONLY that tab
            if target_handle is not None and target_handle in driver.window_handles:
                driver.switch_to.window(target_handle)

                # If this is the last remaining tab in the browser, open a blank tab first
                # so the browser window remains open and alive for future commands
                if len(driver.window_handles) == 1:
                    driver.switch_to.new_window("tab")
                    driver.get("about:blank")
                    driver.switch_to.window(target_handle)
                    driver.close()
                    # Switch to the new blank tab
                    driver.switch_to.window(driver.window_handles[0])
                else:
                    driver.close()
                    # Switch focus to the latest remaining tab
                    remaining_handles = driver.window_handles
                    if remaining_handles:
                        driver.switch_to.window(remaining_handles[-1])

                # Remove closed handle from tracked dictionary
                keys_to_remove = [k for k, h in _tracked_tabs.items() if h == target_handle]
                for k in keys_to_remove:
                    _tracked_tabs.pop(k, None)

                return f"Closed the {target_name.capitalize()} tab."

            # Step 4: Not found
            return f"I couldn't find a tab for '{identifier}' that's currently open."

    except Exception as close_err:
        print(f"[Browser Automation Error] Error closing tab for '{identifier}': {close_err}")
        return f"Sorry, I had trouble closing the tab for '{identifier}'."


def get_open_tabs() -> List[Dict[str, str]]:
    """Returns a list of metadata for all currently open tabs in the automated browser session.

    Useful for diagnostics and automated verification.

    Returns:
        List[Dict[str, str]]: List of dictionaries containing handle, title, and current URL.
    """
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
            # Restore active focus
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
    """Creates a text file safely within the designated Documents/Aetheris directory.

    Strict guardrails:
    - Path traversal protection (strips directory paths, restricts strictly to Documents/Aetheris).
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
            return "Security restriction: Cannot create files outside the Documents/Aetheris folder."

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(str(content))

        return f"Created text file {clean_base} in your Aetheris Documents folder."
    except Exception as e:
        return f"Sorry, could not create text file: {str(e)}"
