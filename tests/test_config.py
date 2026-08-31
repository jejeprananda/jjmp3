"""Tests for config helpers."""

from __future__ import annotations

from mp3dl import config
from mp3dl.config import DEFAULT_WEB_PORT, get_web_port


def test_get_web_port_default(monkeypatch):
    monkeypatch.setattr(config, "load_config", lambda: {})
    assert get_web_port() == DEFAULT_WEB_PORT


def test_get_cache_dir_creates_dir(tmp_path, monkeypatch):
    cache = tmp_path / ".cache" / "jjmp3"
    monkeypatch.setattr(config, "load_config", lambda: {})
    monkeypatch.setattr(config, "DEFAULT_CACHE_DIR", cache)
    path = config.get_cache_dir()
    assert path.is_dir()
