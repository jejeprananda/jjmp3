"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Isolated SQLite database for tests."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("mp3dl.web.models.get_db_path", lambda: db_path)
    from mp3dl.web.models import init_db

    init_db(db_path)
    return db_path


@pytest.fixture
def client(db):
    from mp3dl.web.app import create_app

    return TestClient(create_app())
