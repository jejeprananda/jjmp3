"""API integration tests for local library player."""

from __future__ import annotations

from pathlib import Path

from mp3dl.web.library import upsert_index_entry


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


def test_search_annotates_downloaded(client, download_dir, monkeypatch):
    (download_dir / "Hello.mp3").write_bytes(b"ID3fake")
    upsert_index_entry(
        video_id="abc123",
        filename="Hello.mp3",
        title="Hello",
        channel="Artist",
        duration=120,
        root=download_dir,
    )

    from mp3dl.search import SearchResult

    monkeypatch.setattr(
        "mp3dl.web.api.search.search_youtube",
        lambda q: [
            SearchResult("Hello", "Artist", 120, "abc123", "https://youtu.be/abc123"),
            SearchResult("Other", "B", 90, "xyz", "https://youtu.be/xyz"),
        ],
    )
    r = client.get("/api/search?q=hello")
    assert r.status_code == 200
    data = r.json()
    assert data[0]["downloaded"] is True
    assert data[0]["filename"] == "Hello.mp3"
    assert data[1]["downloaded"] is False


def test_search_annotates_downloaded_by_title(client, download_dir, monkeypatch):
    (download_dir / "Hello.mp3").write_bytes(b"ID3fake")
    upsert_index_entry(
        video_id="abc123",
        filename="Hello.mp3",
        title="Hello",
        channel="Artist",
        duration=120,
        root=download_dir,
    )

    from mp3dl.search import SearchResult

    monkeypatch.setattr(
        "mp3dl.web.api.search.search_youtube",
        lambda q: [
            SearchResult("Hello", "Artist", 120, "different_vid", "https://youtu.be/different_vid"),
        ],
    )
    r = client.get("/api/search?q=hello")
    assert r.status_code == 200
    data = r.json()
    assert data[0]["downloaded"] is True
    assert data[0]["filename"] == "Hello.mp3"


def test_library_scan_and_range(client, download_dir):
    mp3 = download_dir / "Track A.mp3"
    mp3.write_bytes(b"0123456789ABCDEF")
    upsert_index_entry(
        video_id="vid1",
        filename="Track A.mp3",
        title="Track A",
        channel="Ch",
        duration=10,
        root=download_dir,
    )
    r = client.get("/api/library")
    assert r.status_code == 200
    tracks = r.json()["tracks"]
    assert len(tracks) == 1
    assert tracks[0]["filename"] == "Track A.mp3"
    assert tracks[0]["video_id"] == "vid1"

    full = client.get("/api/library/file/Track%20A.mp3")
    assert full.status_code == 200
    assert full.headers.get("accept-ranges") == "bytes"

    partial = client.get(
        "/api/library/file/Track%20A.mp3",
        headers={"Range": "bytes=0-3"},
    )
    assert partial.status_code == 206
    assert partial.content == b"0123"
    assert partial.headers["content-range"].startswith("bytes 0-3/")


def test_delete_file_prunes_playlist(client, download_dir):
    (download_dir / "Gone.mp3").write_bytes(b"x")
    upsert_index_entry(
        video_id="g1",
        filename="Gone.mp3",
        title="Gone",
        root=download_dir,
    )
    r = client.post("/api/playlists", json={"name": "Temp"})
    pid = r.json()["id"]
    client.post(f"/api/playlists/{pid}/tracks", json={"filename": "Gone.mp3"})
    r = client.delete("/api/library/file/Gone.mp3")
    assert r.status_code == 200
    assert not (download_dir / "Gone.mp3").exists()
    pl = client.get(f"/api/playlists/{pid}").json()
    assert pl["tracks"] == []


def test_playlist_crud_and_document(client, download_dir):
    r = client.post("/api/playlists", json={"name": "Workout"})
    assert r.status_code == 200
    pid = r.json()["id"]
    assert (download_dir / "playlists.json").is_file()

    r = client.get("/api/playlists")
    assert any(p["id"] == pid for p in r.json())

    r = client.put(f"/api/playlists/{pid}", json={"name": "Gym"})
    assert r.json()["name"] == "Gym"

    (download_dir / "a.mp3").write_bytes(b"a")
    (download_dir / "b.mp3").write_bytes(b"b")
    client.put(f"/api/playlists/{pid}/tracks", json={"tracks": ["a.mp3", "b.mp3"]})
    pl = client.get(f"/api/playlists/{pid}").json()
    assert pl["tracks"] == ["a.mp3", "b.mp3"]

    doc = client.get("/api/playlists/document").json()
    doc["playlists"][0]["name"] = "Edited"
    r = client.put("/api/playlists/document", json=doc)
    assert r.status_code == 200
    assert r.json()["playlists"][0]["name"] == "Edited"

    r = client.put(
        "/api/playlists/document",
        json={"version": 1, "playlists": [{"id": "bad", "name": "", "tracks": []}]},
    )
    assert r.status_code == 400

    r = client.delete(f"/api/playlists/{pid}")
    assert r.status_code == 200


def test_settings_changes_download_dir(client, download_dir, tmp_path):
    other = tmp_path / "other_music"
    other.mkdir()
    (other / "OnlyHere.mp3").write_bytes(b"zz")

    r = client.put("/api/settings", json={"download_dir": str(other)})
    assert r.status_code == 200
    assert Path(r.json()["download_dir"]) == other.resolve()

    lib = client.get("/api/library").json()
    assert lib["download_dir"] == str(other.resolve())
    assert any(t["filename"] == "OnlyHere.mp3" for t in lib["tracks"])
    assert (other / "playlists.json").is_file()
