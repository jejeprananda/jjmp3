"""SQLite persistence for playlists, tracks, queue, and history."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from mp3dl.config import get_db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS playlists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tracks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    channel     TEXT,
    duration    INTEGER,
    url         TEXT NOT NULL,
    thumbnail   TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS playlist_tracks (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    track_id    INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    PRIMARY KEY (playlist_id, track_id)
);

CREATE TABLE IF NOT EXISTS queue (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id    INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    added_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id    INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    played_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@dataclass(frozen=True)
class Playlist:
    id: int
    name: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Track:
    id: int
    video_id: str
    title: str
    channel: str | None
    duration: int | None
    url: str
    thumbnail: str | None


@dataclass(frozen=True)
class QueueItem:
    id: int
    track: Track
    position: int
    added_at: str


def _connect(db_path=None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None) -> None:
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def _row_to_track(row: sqlite3.Row) -> Track:
    return Track(
        id=row["id"],
        video_id=row["video_id"],
        title=row["title"],
        channel=row["channel"],
        duration=row["duration"],
        url=row["url"],
        thumbnail=row["thumbnail"],
    )


def _row_to_playlist(row: sqlite3.Row) -> Playlist:
    return Playlist(
        id=row["id"],
        name=row["name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def create_playlist(name: str) -> int:
    now = _now()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO playlists (name, created_at, updated_at) VALUES (?, ?, ?)",
            (name.strip(), now, now),
        )
        return int(cur.lastrowid)


def list_playlists() -> list[Playlist]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM playlists ORDER BY updated_at DESC, id ASC"
        ).fetchall()
    return [_row_to_playlist(r) for r in rows]


def get_playlist(playlist_id: int) -> Playlist | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM playlists WHERE id = ?", (playlist_id,)
        ).fetchone()
    return _row_to_playlist(row) if row else None


def rename_playlist(playlist_id: int, name: str) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE playlists SET name = ?, updated_at = ? WHERE id = ?",
            (name.strip(), _now(), playlist_id),
        )
        return cur.rowcount > 0


def delete_playlist(playlist_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        return cur.rowcount > 0


def upsert_track(
    video_id: str,
    title: str,
    channel: str | None,
    duration: int | None,
    url: str,
    thumbnail: str | None,
) -> int:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO tracks (video_id, title, channel, duration, url, thumbnail)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                title = excluded.title,
                channel = excluded.channel,
                duration = excluded.duration,
                url = excluded.url,
                thumbnail = excluded.thumbnail
            """,
            (video_id, title, channel, duration, url, thumbnail),
        )
        row = conn.execute(
            "SELECT id FROM tracks WHERE video_id = ?", (video_id,)
        ).fetchone()
        assert row is not None
        return int(row["id"])


def get_track(track_id: int) -> Track | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
    return _row_to_track(row) if row else None


def get_track_by_video_id(video_id: str) -> Track | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM tracks WHERE video_id = ?", (video_id,)
        ).fetchone()
    return _row_to_track(row) if row else None


def add_track_to_playlist(playlist_id: int, track_id: int) -> None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos "
            "FROM playlist_tracks WHERE playlist_id = ?",
            (playlist_id,),
        ).fetchone()
        position = int(row["next_pos"]) if row else 0
        conn.execute(
            """
            INSERT INTO playlist_tracks (playlist_id, track_id, position)
            VALUES (?, ?, ?)
            ON CONFLICT(playlist_id, track_id) DO NOTHING
            """,
            (playlist_id, track_id, position),
        )
        conn.execute(
            "UPDATE playlists SET updated_at = ? WHERE id = ?",
            (_now(), playlist_id),
        )


def remove_track_from_playlist(playlist_id: int, track_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
            (playlist_id, track_id),
        )
        if cur.rowcount:
            conn.execute(
                "UPDATE playlists SET updated_at = ? WHERE id = ?",
                (_now(), playlist_id),
            )
        return cur.rowcount > 0


def list_playlist_tracks(playlist_id: int) -> list[Track]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT t.* FROM tracks t
            JOIN playlist_tracks pt ON pt.track_id = t.id
            WHERE pt.playlist_id = ?
            ORDER BY pt.position ASC, pt.track_id ASC
            """,
            (playlist_id,),
        ).fetchall()
    return [_row_to_track(r) for r in rows]


def reorder_playlist_tracks(playlist_id: int, track_ids: list[int]) -> None:
    with _connect() as conn:
        for position, track_id in enumerate(track_ids):
            conn.execute(
                """
                UPDATE playlist_tracks SET position = ?
                WHERE playlist_id = ? AND track_id = ?
                """,
                (position, playlist_id, track_id),
            )
        conn.execute(
            "UPDATE playlists SET updated_at = ? WHERE id = ?",
            (_now(), playlist_id),
        )


def list_queue() -> list[QueueItem]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT q.id AS queue_id, q.position, q.added_at, t.*
            FROM queue q
            JOIN tracks t ON t.id = q.track_id
            ORDER BY q.position ASC, q.id ASC
            """
        ).fetchall()
    return [
        QueueItem(
            id=row["queue_id"],
            track=_row_to_track(row),
            position=row["position"],
            added_at=row["added_at"],
        )
        for row in rows
    ]


def add_to_queue(track_id: int) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM queue"
        ).fetchone()
        position = int(row["next_pos"]) if row else 0
        cur = conn.execute(
            "INSERT INTO queue (track_id, position) VALUES (?, ?)",
            (track_id, position),
        )
        return int(cur.lastrowid)


def add_playlist_to_queue(playlist_id: int) -> int:
    tracks = list_playlist_tracks(playlist_id)
    count = 0
    for track in tracks:
        add_to_queue(track.id)
        count += 1
    return count


def remove_from_queue(queue_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM queue WHERE id = ?", (queue_id,))
        return cur.rowcount > 0


def clear_queue() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM queue")


def reorder_queue(queue_ids: list[int]) -> None:
    with _connect() as conn:
        for position, queue_id in enumerate(queue_ids):
            conn.execute(
                "UPDATE queue SET position = ? WHERE id = ?",
                (position, queue_id),
            )


def log_history(track_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO history (track_id, played_at) VALUES (?, ?)",
            (track_id, _now()),
        )


def list_history(limit: int = 50) -> list[Track]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT t.* FROM history h
            JOIN tracks t ON t.id = h.track_id
            ORDER BY h.played_at DESC, h.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_track(r) for r in rows]


def track_to_dict(track: Track) -> dict:
    return {
        "id": track.id,
        "video_id": track.video_id,
        "title": track.title,
        "channel": track.channel,
        "duration": track.duration,
        "url": track.url,
        "thumbnail": track.thumbnail,
    }


def playlist_to_dict(playlist: Playlist) -> dict:
    return {
        "id": playlist.id,
        "name": playlist.name,
        "created_at": playlist.created_at,
        "updated_at": playlist.updated_at,
    }
