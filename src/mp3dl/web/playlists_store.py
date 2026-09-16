"""JSON playlist store living inside the download directory."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from fastapi import HTTPException

from mp3dl.config import get_download_dir

PLAYLISTS_FILENAME = "playlists.json"
_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def playlists_path(root: Path | None = None) -> Path:
    return (root or get_download_dir()) / PLAYLISTS_FILENAME


def empty_doc() -> dict:
    return {"version": 1, "playlists": []}


def load_playlists(root: Path | None = None) -> dict:
    root = root or get_download_dir()
    root.mkdir(parents=True, exist_ok=True)
    path = playlists_path(root)
    if not path.is_file():
        doc = empty_doc()
        save_playlists(doc, root)
        return doc
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"Invalid playlists.json: {exc}") from exc
    return validate_playlists_doc(data)


def save_playlists(data: dict, root: Path | None = None) -> dict:
    root = root or get_download_dir()
    root.mkdir(parents=True, exist_ok=True)
    doc = validate_playlists_doc(data)
    playlists_path(root).write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return doc


def validate_playlists_doc(data: object) -> dict:
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="playlists.json must be an object")
    version = data.get("version", 1)
    if version != 1:
        raise HTTPException(status_code=400, detail="Unsupported playlists.json version")
    playlists = data.get("playlists")
    if not isinstance(playlists, list):
        raise HTTPException(status_code=400, detail="playlists must be a list")
    seen_ids: set[str] = set()
    cleaned = []
    for i, item in enumerate(playlists):
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail=f"playlists[{i}] must be an object")
        pid = item.get("id")
        name = item.get("name")
        tracks = item.get("tracks", [])
        if not isinstance(pid, str) or not _ID_RE.match(pid):
            raise HTTPException(status_code=400, detail=f"playlists[{i}].id invalid")
        if pid in seen_ids:
            raise HTTPException(status_code=400, detail=f"Duplicate playlist id: {pid}")
        seen_ids.add(pid)
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=400, detail=f"playlists[{i}].name required")
        if not isinstance(tracks, list) or not all(isinstance(t, str) for t in tracks):
            raise HTTPException(
                status_code=400,
                detail=f"playlists[{i}].tracks must be a list of filenames",
            )
        cleaned.append(
            {
                "id": pid,
                "name": name.strip(),
                "tracks": list(tracks),
            }
        )
    return {"version": 1, "playlists": cleaned}


def list_playlists(root: Path | None = None) -> list[dict]:
    return load_playlists(root)["playlists"]


def get_playlist(playlist_id: str, root: Path | None = None) -> dict | None:
    for pl in list_playlists(root):
        if pl["id"] == playlist_id:
            return pl
    return None


def create_playlist(name: str, root: Path | None = None) -> dict:
    root = root or get_download_dir()
    doc = load_playlists(root)
    playlist = {
        "id": f"pl_{uuid.uuid4().hex[:10]}",
        "name": name.strip(),
        "tracks": [],
    }
    if not playlist["name"]:
        raise HTTPException(status_code=400, detail="Name required")
    doc["playlists"].append(playlist)
    save_playlists(doc, root)
    return playlist


def rename_playlist(playlist_id: str, name: str, root: Path | None = None) -> dict:
    root = root or get_download_dir()
    doc = load_playlists(root)
    name = name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    for pl in doc["playlists"]:
        if pl["id"] == playlist_id:
            pl["name"] = name
            save_playlists(doc, root)
            return pl
    raise HTTPException(status_code=404, detail="Playlist not found")


def delete_playlist(playlist_id: str, root: Path | None = None) -> None:
    root = root or get_download_dir()
    doc = load_playlists(root)
    before = len(doc["playlists"])
    doc["playlists"] = [p for p in doc["playlists"] if p["id"] != playlist_id]
    if len(doc["playlists"]) == before:
        raise HTTPException(status_code=404, detail="Playlist not found")
    save_playlists(doc, root)


def set_playlist_tracks(
    playlist_id: str, tracks: list[str], root: Path | None = None
) -> dict:
    root = root or get_download_dir()
    doc = load_playlists(root)
    if not isinstance(tracks, list) or not all(isinstance(t, str) for t in tracks):
        raise HTTPException(status_code=400, detail="tracks must be list of filenames")
    for pl in doc["playlists"]:
        if pl["id"] == playlist_id:
            pl["tracks"] = list(tracks)
            save_playlists(doc, root)
            return pl
    raise HTTPException(status_code=404, detail="Playlist not found")


def add_track_to_playlist(
    playlist_id: str, filename: str, root: Path | None = None
) -> dict:
    root = root or get_download_dir()
    pl = get_playlist(playlist_id, root)
    if pl is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    tracks = list(pl["tracks"])
    if filename not in tracks:
        tracks.append(filename)
    return set_playlist_tracks(playlist_id, tracks, root)


def remove_track_from_playlist(
    playlist_id: str, filename: str, root: Path | None = None
) -> dict:
    root = root or get_download_dir()
    pl = get_playlist(playlist_id, root)
    if pl is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    tracks = [t for t in pl["tracks"] if t != filename]
    return set_playlist_tracks(playlist_id, tracks, root)


def prune_filename_from_all(filename: str, root: Path | None = None) -> int:
    """Remove a filename from every playlist. Returns number of playlists touched."""
    root = root or get_download_dir()
    doc = load_playlists(root)
    touched = 0
    for pl in doc["playlists"]:
        before = len(pl["tracks"])
        pl["tracks"] = [t for t in pl["tracks"] if t != filename]
        if len(pl["tracks"]) != before:
            touched += 1
    if touched:
        save_playlists(doc, root)
    return touched
