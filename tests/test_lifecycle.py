"""Lifecycle API and shutdown tracking."""

from __future__ import annotations

import time

from mp3dl.web import lifecycle


def test_ping_and_quit(client):
    lifecycle.reset_for_tests()
    r = client.post("/api/lifecycle/ping", json={"tab_id": "tab-a"})
    assert r.status_code == 200
    r = client.post("/api/lifecycle/quit", json={"tab_id": "tab-a"})
    assert r.status_code == 200


def test_watchdog_triggers_shutdown():
    lifecycle.reset_for_tests()
    fired = []

    lifecycle.set_shutdown_callback(lambda: fired.append(True))
    lifecycle.start_watchdog()
    lifecycle.ping_tab("tab-1")
    lifecycle.quit_tab("tab-1")
    time.sleep(0.05)
    assert fired == [True]
