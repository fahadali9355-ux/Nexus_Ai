"""Local Fast-Path Router for deterministic action commands in Nexus.

Bypasses cloud LLM API calls (Gemini) for instant, local execution of 1:1 commands
(e.g., opening apps/websites, closing tabs, volume adjustment, screenshots, system info).
"""

import re
from typing import Callable, List, Optional, Tuple

from modules.task_executor import (
    KNOWN_APPS,
    KNOWN_SERVICES,
    close_website,
    get_system_info,
    open_application,
    open_website,
    set_system_volume,
    take_screenshot,
)


def _handle_open(target: str) -> str:
    """Smart dispatcher for opening desktop applications or websites."""
    clean = target.strip().lower()
    # Strip conversational noise words like 'the', 'app', 'application', 'website', 'page'
    clean = re.sub(r"^(?:the\s+)", "", clean)
    clean = re.sub(r"\s+(?:app|application|website|webpage|page|site)$", "", clean).strip()

    # 1. If recognized desktop application
    if clean in KNOWN_APPS:
        return open_application(clean)

    # 2. If recognized web service or URL / domain
    if (
        clean in KNOWN_SERVICES
        or clean.startswith("http://")
        or clean.startswith("https://")
        or ("." in clean and " " not in clean)
    ):
        return open_website(clean)

    # 3. Fallback: Check if target can be opened as application or website
    return open_website(clean)


def _handle_close(target: str) -> str:
    """Closes a specific tab in the automated browser."""
    clean = target.strip().lower()
    clean = re.sub(r"^(?:the\s+|that\s+)", "", clean)
    clean = re.sub(r"\s+(?:tab|website|webpage|page|site)$", "", clean).strip()
    return close_website(clean)


def _handle_volume(match: re.Match, text: str) -> str:
    """Handles volume adjustments (percentage, mute, unmute, up, down)."""
    raw = text.lower()
    if "mute" in raw and "unmute" not in raw:
        return set_system_volume(0)
    if "unmute" in raw:
        return set_system_volume(50)
    if "up" in raw or "increase" in raw or "raise" in raw:
        return set_system_volume(80)
    if "down" in raw or "lower" in raw or "decrease" in raw:
        return set_system_volume(30)

    # Extract volume percentage number
    num_match = re.search(r"\b(\d{1,3})\b", raw)
    if num_match:
        level = int(num_match.group(1))
        return set_system_volume(level)
    return set_system_volume(50)


def _handle_search(query: str) -> str:
    """Executes a direct web search."""
    clean = query.strip()
    return open_website(clean)


# =====================================================================
# Shutdown / Stop / Exit Command Patterns
# =====================================================================
SHUTDOWN_PATTERNS: List[str] = [
    r"^(?:please\s+)?(?:nexus\s+)?(?:shut\s*down|shutdown|power\s*off|turn\s*off|turn\s*yourself\s*off)(?:\s+(?:nexus|the\s+system|system|assistant))?$",
    r"^(?:please\s+)?(?:nexus\s+)?(?:go\s+to\s+sleep|sleep)(?:\s+(?:nexus|now))?$",
    r"^(?:please\s+)?(?:nexus\s+)?(?:exit|quit|terminate)(?:\s+(?:nexus|program|app|application|assistant|the\s+system|system))?$",
    r"^(?:please\s+)?(?:nexus\s+)?(?:goodbye|bye)(?:\s+(?:nexus|assistant))?$",
    r"^(?:please\s+)?(?:nexus\s+)?(?:stop\s+listening|stop)(?:\s+(?:nexus|assistant|now))?$",
]


def is_shutdown_command(text: str) -> bool:
    """Checks whether a command specifically requests shutting down, sleeping, or stopping Nexus."""
    if not text or not text.strip():
        return False
    clean = text.strip().lower().rstrip(".!?,;")
    return any(re.search(pat, clean) for pat in SHUTDOWN_PATTERNS)


# =====================================================================
# Extensible Fast-Path Rules Table
# (regex_pattern, handler_function)
# To add a new fast-path command, simply append a tuple to this list!
# =====================================================================
FAST_PATH_RULES: List[Tuple[str, Callable[[re.Match, str], str]]] = [
    # 1. Voice Shutdown / Exit / Stop commands (e.g. 'nexus stop', 'shut down', 'go to sleep', 'exit') - Highest Priority
    (
        r"^(?:please\s+)?(?:nexus\s+)?(?:shut\s*down|shutdown|power\s*off|turn\s*off|turn\s*yourself\s*off|go\s+to\s+sleep|sleep|exit|quit|terminate|goodbye|bye|stop\s+listening|stop)(?:\s+(?:nexus|assistant|program|the\s+system|system|now))?$",
        lambda m, text: "Shutting down Nexus. Goodbye!",
    ),
    # 2. App / Website opening (e.g. 'open instagram', 'launch notepad', 'start chrome', 'open https://google.com')
    (
        r"^(?:please\s+)?(?:open|launch|start|browse\s+to)\s+(?:website\s+|app\s+|application\s+)?([a-zA-Z0-9_\.\-]+(?:\s+[a-zA-Z0-9_\.\-]+)?)$",
        lambda m, text: _handle_open(m.group(1)),
    ),
    # 3. Tab closing (e.g. 'close youtube tab', 'close that github tab', 'close instagram')
    (
        r"^(?:please\s+)?(?:close|shut)\s+(?:the\s+|that\s+)?(?!down\b)([a-zA-Z0-9_\.\-]+(?:\s+[a-zA-Z0-9_\.\-]+)?\s+tab|[a-zA-Z0-9_\.\-]+)$",
        lambda m, text: _handle_close(m.group(1)),
    ),
    # 4. Explicit Volume setting (e.g. 'set volume to 50', 'volume 70', 'turn volume to 30')
    (
        r"\b(?:set|change|turn|adjust)\s+(?:the\s+)?volume\s+(?:to\s+)?\d+\b|\bvolume\s+to\s+\d+\b|\bvolume\s+\d+\b",
        _handle_volume,
    ),
    # 5. Mute / Unmute / Volume Up / Volume Down
    (
        r"\b(?:mute|unmute)\s*(?:the\s+)?(?:volume|sound|audio)?\b|\b(?:turn\s+up|turn\s+down|volume\s+up|volume\s+down)\b",
        _handle_volume,
    ),
    # 6. Screenshot capture (e.g. 'take a screenshot', 'capture screen', 'screen capture')
    (
        r"\b(?:take\s+(?:a\s+)?screenshot|capture\s+(?:the\s+)?screen|screen\s*capture)\b",
        lambda m, text: take_screenshot(),
    ),
    # 7. System status, date, time, battery queries
    (
        r"^(?:what\s+time\s+is\s+it|what\s+is\s+the\s+time|current\s+time|what\s+date\s+is\s+it|today's\s+date|system\s+info(?:rmation)?|battery\s+(?:status|level|percent)|how\s+is\s+my\s+battery)\b",
        lambda m, text: get_system_info(),
    ),
    # 8. Direct web search (e.g. 'search google for artificial intelligence', 'search for weather today')
    (
        r"^(?:search\s+(?:google\s+for|for|google)|google)\s+(.+)$",
        lambda m, text: _handle_search(m.group(1)),
    ),
]


def try_local_fast_path(user_text: str) -> Optional[str]:
    """Attempts to match and execute deterministic system commands locally without Gemini API latency.

    Args:
        user_text (str): Spoken or typed user command.

    Returns:
        Optional[str]: Execution response string if handled locally, or None to fall back to Gemini.
    """
    if not user_text or not user_text.strip():
        return None

    cleaned = user_text.strip()
    lower_text = cleaned.lower()

    for pattern, handler in FAST_PATH_RULES:
        match = re.search(pattern, lower_text)
        if match:
            try:
                response = handler(match, cleaned)
                if response:
                    return response
            except Exception as err:
                print(f"[Fast-Path Warning] Local execution failed for '{user_text}': {err}. Falling through to Gemini...")
                return None

    return None


__all__ = ["try_local_fast_path", "FAST_PATH_RULES", "is_shutdown_command", "SHUTDOWN_PATTERNS"]
