"""Unit tests for library index and playlist JSON store."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from mp3dl.web.library import (
    find_by_video_id,
    scan_library,
    unique_filename,
    upsert_index_entry,
)
from mp3dl.web.playlists_store import (
    create_playlist,
    load_playlists,
    prune_filename_from_all,
    save_playlists,
    set_playlist_tracks,
    validate_playlists_doc,
)


def test_index_and_scan(download_dir):
    (download_dir / "Song.mp3").write_bytes(b"abc")
    (download_dir / "manual.mp3").write_bytes(b"def")
    upsert_index_entry(
        video_id="v1",
        filename="Song.mp3",
        title="Song",
        channel="A",
        duration=30,
        root=download_dir,
    )
    assert find_by_video_id("v1", download_dir)["filename"] == "Song.mp3"
    tracks = scan_library(download_dir)
    names = {t["filename"] for t in tracks}
    assert names == {"Song.mp3", "manual.mp3"}
    manual = next(t for t in tracks if t["filename"] == "manual.mp3")
    assert manual["video_id"] is None


def test_unique_filename_collision(download_dir):
    (download_dir / "Hit.mp3").write_bytes(b"x")
    upsert_index_entry(
        video_id="old",
        filename="Hit.mp3",
        title="Hit",
        root=download_dir,
    )
    assert unique_filename("Hit", "new", download_dir) == "Hit [new].mp3"
    assert unique_filename("Hit", "old", download_dir) == "Hit.mp3"


def test_playlists_validate_and_prune(download_dir):
    pl = create_playlist("One", download_dir)
    set_playlist_tracks(pl["id"], ["a.mp3", "b.mp3"], download_dir)
    assert prune_filename_from_all("a.mp3", download_dir) == 1
    doc = load_playlists(download_dir)
    assert doc["playlists"][0]["tracks"] == ["b.mp3"]

    with pytest.raises(HTTPException):
        validate_playlists_doc({"version": 2, "playlists": []})

    with pytest.raises(HTTPException):
        save_playlists(
            {
                "version": 1,
                "playlists": [{"id": "x!", "name": "Bad", "tracks": []}],
            },
            download_dir,
        )
