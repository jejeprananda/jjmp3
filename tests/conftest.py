"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def download_dir(tmp_path, monkeypatch):
    """Isolated download directory + config for tests."""
    root = (tmp_path / "music").resolve()
    root.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "config.json"

    monkeypatch.setattr("mp3dl.config.CONFIG_DIR", config_dir)
    monkeypatch.setattr("mp3dl.config.CONFIG_PATH", config_path)
    monkeypatch.setattr("mp3dl.config.DEFAULT_DOWNLOAD_DIR", root)
    monkeypatch.setattr("mp3dl.config.DB_PATH", config_dir / "jjmp3.db")

    state = {"dir": root}

    def get_dir() -> Path:
        return state["dir"]

    def set_dir(path: str | Path) -> Path:
        resolved = Path(path).expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        state["dir"] = resolved
        data = {}
        if config_path.is_file():
            import json

            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
        data["download_dir"] = str(resolved)
        config_path.write_text(
            __import__("json").dumps(data, indent=2) + "\n",
            encoding="utf-8",
        )
        return resolved

    targets = [
        "mp3dl.config.get_download_dir",
        "mp3dl.config.set_download_dir",
        "mp3dl.web.library.get_download_dir",
        "mp3dl.web.playlists_store.get_download_dir",
        "mp3dl.web.api.library.get_download_dir",
        "mp3dl.web.api.settings.get_download_dir",
        "mp3dl.web.api.settings.set_download_dir",
        "mp3dl.web.jobs.get_download_dir",
        "mp3dl.web.app.get_download_dir",
    ]
    for target in targets:
        if target.endswith("set_download_dir"):
            monkeypatch.setattr(target, set_dir)
        else:
            monkeypatch.setattr(target, get_dir)

    return root


@pytest.fixture
def client(download_dir):
    from mp3dl.web.app import create_app

    return TestClient(create_app())
