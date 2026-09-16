"""Update API tests."""

from __future__ import annotations


def test_update_check_up_to_date(client, monkeypatch):
    monkeypatch.setattr(
        "mp3dl.web.api.update.check_update",
        lambda: {
            "local_version": "0.4.0",
            "remote_version": "0.4.0",
            "update_available": False,
            "error": None,
        },
    )
    r = client.get("/api/update/check")
    assert r.status_code == 200
    assert r.json()["update_available"] is False


def test_update_check_available(client, monkeypatch):
    monkeypatch.setattr(
        "mp3dl.web.api.update.check_update",
        lambda: {
            "local_version": "0.3.0",
            "remote_version": "0.4.0",
            "update_available": True,
            "error": None,
        },
    )
    r = client.get("/api/update/check")
    assert r.json()["update_available"] is True


def test_settings_includes_version(client, monkeypatch):
    monkeypatch.setattr("mp3dl.web.api.settings.get_local_version", lambda: "0.4.0")
    r = client.get("/api/settings")
    assert r.json()["version"] == "0.4.0"
