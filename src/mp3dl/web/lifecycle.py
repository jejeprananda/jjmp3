"""Browser session lifecycle — shutdown server when all UI tabs close."""

from __future__ import annotations

import threading
import time
from typing import Callable

_LOCK = threading.Lock()
_TABS: dict[str, float] = {}
_HAD_CLIENT = False
_SHUTDOWN: Callable[[], None] | None = None

PING_INTERVAL_HINT = 4.0
STALE_AFTER = 10.0
WATCH_INTERVAL = 1.0


def set_shutdown_callback(fn: Callable[[], None]) -> None:
    global _SHUTDOWN
    _SHUTDOWN = fn


def ping_tab(tab_id: str) -> None:
    global _HAD_CLIENT
    if not tab_id:
        return
    now = time.monotonic()
    with _LOCK:
        _HAD_CLIENT = True
        _TABS[tab_id] = now


def quit_tab(tab_id: str) -> None:
    if not tab_id:
        return
    with _LOCK:
        _TABS.pop(tab_id, None)
    _maybe_shutdown()


def _maybe_shutdown() -> None:
    with _LOCK:
        active = bool(_TABS)
    if not active and _HAD_CLIENT:
        _trigger_shutdown()


def _trigger_shutdown() -> None:
    if _SHUTDOWN is not None:
        _SHUTDOWN()


def start_watchdog() -> None:
    def _run() -> None:
        while True:
            time.sleep(WATCH_INTERVAL)
            now = time.monotonic()
            with _LOCK:
                if not _HAD_CLIENT:
                    continue
                stale = [
                    tid
                    for tid, seen in list(_TABS.items())
                    if now - seen > STALE_AFTER
                ]
                for tid in stale:
                    _TABS.pop(tid, None)
                active = bool(_TABS)
            if _HAD_CLIENT and not active:
                _trigger_shutdown()
                return

    threading.Thread(target=_run, daemon=True).start()


def reset_for_tests() -> None:
    global _HAD_CLIENT, _SHUTDOWN
    with _LOCK:
        _TABS.clear()
        _HAD_CLIENT = False
    _SHUTDOWN = None
