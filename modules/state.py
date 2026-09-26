"""Thread-safe global state manager for Nexus Voice Assistant & Flask Dashboard."""

from datetime import datetime
import threading
import time
from typing import Any, Dict, List, Optional


class StateManager:
    """Thread-safe manager for tracking assistant status and interaction history."""

    def __init__(self, max_history: int = 100):
        self._lock = threading.Lock()
        self._max_history = max_history
        self._status: str = "Idle / Listening for wake word"
        self._active_module: Optional[str] = "Wake Word Engine"
        self._last_heard: Optional[str] = None
        self._last_response: Optional[str] = None
        self._last_updated: float = time.time()
        self._start_time: float = time.time()
        self._history: List[Dict[str, Any]] = []
        self._cycle_counter: int = 0
        self._is_running: bool = True
        self._pending_action: Optional[Dict[str, Any]] = None

    def set_pending_action(self, action: Dict[str, Any], timeout_seconds: float = 90.0) -> None:
        """Sets a lightweight pending action for multi-step or clarifying confirmation."""
        with self._lock:
            action_data = dict(action)
            action_data["timestamp"] = time.time()
            action_data["expires_at"] = time.time() + timeout_seconds
            self._pending_action = action_data

    def get_pending_action(self) -> Optional[Dict[str, Any]]:
        """Returns the active pending action if not expired, or None."""
        with self._lock:
            if not self._pending_action:
                return None
            if time.time() > self._pending_action.get("expires_at", 0):
                self._pending_action = None
                return None
            return dict(self._pending_action)

    def clear_pending_action(self) -> None:
        """Clears any active pending action."""
        with self._lock:
            self._pending_action = None

    def set_status(
        self,
        status: str,
        active_module: Optional[str] = None,
        last_heard: Optional[str] = None,
        last_response: Optional[str] = None,
    ) -> None:
        """Updates the current assistant status in a thread-safe manner."""
        with self._lock:
            self._status = status
            if active_module is not None:
                self._active_module = active_module
            if last_heard is not None:
                self._last_heard = last_heard
            if last_response is not None:
                self._last_response = last_response
            self._last_updated = time.time()

    def add_history(
        self,
        heard: str,
        handler: str,
        response: str,
        status: str = "success",
    ) -> Dict[str, Any]:
        """Appends a new interaction entry to the history."""
        with self._lock:
            self._cycle_counter += 1
            entry = {
                "id": self._cycle_counter,
                "timestamp": datetime.now().strftime("%I:%M:%S %p"),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "heard": heard,
                "handler": handler,
                "response": response,
                "status": status,
            }
            # Prepend newest interactions first
            self._history.insert(0, entry)
            if len(self._history) > self._max_history:
                self._history.pop()
            self._last_updated = time.time()
            return entry

    def get_status(self) -> Dict[str, Any]:
        """Returns the current state snapshot as a JSON-serializable dictionary."""
        with self._lock:
            uptime = int(time.time() - self._start_time)
            return {
                "status": self._status,
                "active_module": self._active_module,
                "last_heard": self._last_heard,
                "last_response": self._last_response,
                "last_updated": self._last_updated,
                "total_cycles": self._cycle_counter,
                "uptime_seconds": uptime,
                "is_running": self._is_running,
            }

    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Returns a copy of the interaction history."""
        with self._lock:
            if limit:
                return list(self._history[:limit])
            return list(self._history)

    def clear_history(self) -> None:
        """Clears the interaction history log."""
        with self._lock:
            self._history.clear()
            self._last_updated = time.time()


# Global singleton instance
state = StateManager()
