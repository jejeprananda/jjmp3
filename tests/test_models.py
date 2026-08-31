"""Tests for SQLite models."""

from __future__ import annotations

from mp3dl.web.models import (
    add_to_queue,
    add_track_to_playlist,
    create_playlist,
    get_track,
    list_playlists,
    list_queue,
    log_history,
    upsert_track,
)


def test_create_and_list_playlist(db):
    create_playlist("Favorit")
    playlists = list_playlists()
    assert len(playlists) == 1
    assert playlists[0].name == "Favorit"


def test_upsert_track_dedup(db):
    id1 = upsert_track(
        "abc123",
        "Song",
        "Artist",
        180,
        "https://youtube.com/watch?v=abc123",
        None,
    )
    id2 = upsert_track(
        "abc123",
        "Song Updated",
        "Artist",
        180,
        "https://youtube.com/watch?v=abc123",
        None,
    )
    assert id1 == id2
    assert get_track(id1).title == "Song Updated"


def test_playlist_and_queue(db):
    pid = create_playlist("Work")
    tid = upsert_track(
        "vid1",
        "Track",
        "Ch",
        120,
        "https://youtube.com/watch?v=vid1",
        None,
    )
    add_track_to_playlist(pid, tid)
    qid = add_to_queue(tid)
    assert qid > 0
    assert len(list_queue()) == 1
    log_history(tid)
