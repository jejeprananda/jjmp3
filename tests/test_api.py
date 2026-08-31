"""API integration tests."""

from __future__ import annotations


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_search_requires_query(client):
    r = client.get("/api/search")
    assert r.status_code == 400


def test_search_empty_query(client):
    r = client.get("/api/search?q=")
    assert r.status_code == 400


def test_playlist_crud(client):
    r = client.post("/api/playlists", json={"name": "Test"})
    assert r.status_code == 200
    pid = r.json()["id"]
    r = client.get("/api/playlists")
    assert any(p["id"] == pid for p in r.json())
    r = client.put(f"/api/playlists/{pid}", json={"name": "Renamed"})
    assert r.json()["name"] == "Renamed"
    r = client.delete(f"/api/playlists/{pid}")
    assert r.status_code == 200
