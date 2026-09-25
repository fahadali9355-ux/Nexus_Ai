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


def open_website(url_or_search_term: str) -> str:
    """Opens default browser to a URL or performs a Google search query.

    Args:
        url_or_search_term (str): Web address or search keywords.

    Returns:
        str: TTS-friendly confirmation message.
    """
    if not url_or_search_term or not str(url_or_search_term).strip():
        return "Please specify a URL or search query to open."

    target = str(url_or_search_term).strip()

    try:
        # Check if it's a direct URL
        if target.startswith("http://") or target.startswith("https://"):
            webbrowser.open(target)
            return f"Opening {target} in your browser."
        elif "." in target and " " not in target:
            full_url = f"https://{target}"
            webbrowser.open(full_url)
            return f"Opening {target} in your browser."
        else:
            query_enc = urllib.parse.quote_plus(target)
            search_url = f"https://www.google.com/search?q={query_enc}"
            webbrowser.open(search_url)
            return f"Searching Google for {target}."
    except Exception as e:
        return f"Sorry, could not open web link: {str(e)}"


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
