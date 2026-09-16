"""Local download-folder library: scan, index, Range serve, delete."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, Response

from mp3dl.config import get_download_dir

LIBRARY_FILENAME = "library.json"
COVERS_DIRNAME = "covers"
_SAFE_REL = re.compile(r"^[^.].*")


def library_path(root: Path | None = None) -> Path:
    return (root or get_download_dir()) / LIBRARY_FILENAME


def covers_dir(root: Path | None = None) -> Path:
    path = (root or get_download_dir()) / COVERS_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_index(root: Path | None = None) -> dict:
    path = library_path(root)
    if not path.is_file():
        return {"version": 1, "tracks": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "tracks": []}
    if not isinstance(data, dict):
        return {"version": 1, "tracks": []}
    tracks = data.get("tracks")
    if not isinstance(tracks, list):
        data["tracks"] = []
    data.setdefault("version", 1)
    return data


def save_index(data: dict, root: Path | None = None) -> None:
    root = root or get_download_dir()
    root.mkdir(parents=True, exist_ok=True)
    path = library_path(root)
    payload = {
        "version": int(data.get("version", 1)),
        "tracks": list(data.get("tracks") or []),
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def find_by_video_id(video_id: str, root: Path | None = None) -> dict | None:
    for track in load_index(root).get("tracks", []):
        if isinstance(track, dict) and track.get("video_id") == video_id:
            filename = track.get("filename")
            if filename and (root or get_download_dir()).joinpath(filename).is_file():
                return track
    return None


def find_by_filename(filename: str, root: Path | None = None) -> dict | None:
    for track in load_index(root).get("tracks", []):
        if isinstance(track, dict) and track.get("filename") == filename:
            return track
    return None


_NORM_RE = re.compile(r"[^a-z0-9]+")


def _normalize_title(value: str | None) -> str:
    """Normalize titles for dedup comparisons (case/spacing/punctuation agnostic)."""
    if not value:
        return ""
    lowered = str(value).strip().lower()
    lowered = _NORM_RE.sub(" ", lowered)
    return " ".join(lowered.split())


def find_by_title(title: str, root: Path | None = None) -> dict | None:
    """Find an already-downloaded track by matching normalized title."""
    norm = _normalize_title(title)
    if not norm:
        return None

    root = root or get_download_dir()
    for track in load_index(root).get("tracks", []):
        if not isinstance(track, dict):
            continue
        track_title = track.get("title") or ""
        if _normalize_title(track_title) != norm:
            continue
        filename = track.get("filename")
        if filename and root.joinpath(filename).is_file():
            return track
    return None


def upsert_index_entry(
    *,
    video_id: str,
    filename: str,
    title: str,
    channel: str | None = None,
    duration: int | None = None,
    cover: str | None = None,
    root: Path | None = None,
) -> dict:
    root = root or get_download_dir()
    data = load_index(root)
    tracks = [t for t in data.get("tracks", []) if isinstance(t, dict)]
    entry = {
        "video_id": video_id,
        "filename": filename,
        "title": title,
        "channel": channel or "",
        "duration": duration,
        "cover": cover,
    }
    replaced = False
    for i, existing in enumerate(tracks):
        if existing.get("video_id") == video_id or existing.get("filename") == filename:
            tracks[i] = {**existing, **{k: v for k, v in entry.items() if v is not None}}
            entry = tracks[i]
            replaced = True
            break
    if not replaced:
        tracks.append(entry)
    data["tracks"] = tracks
    save_index(data, root)
    return entry


def remove_from_index(filename: str, root: Path | None = None) -> dict | None:
    root = root or get_download_dir()
    data = load_index(root)
    removed = None
    kept = []
    for track in data.get("tracks", []):
        if isinstance(track, dict) and track.get("filename") == filename:
            removed = track
            continue
        kept.append(track)
    data["tracks"] = kept
    save_index(data, root)
    return removed


def scan_library(root: Path | None = None) -> list[dict]:
    """Disk is source of truth; enrich with library.json metadata when present."""
    root = root or get_download_dir()
    root.mkdir(parents=True, exist_ok=True)
    index_by_file = {
        t["filename"]: t
        for t in load_index(root).get("tracks", [])
        if isinstance(t, dict) and t.get("filename")
    }
    results: list[dict] = []
    for path in sorted(root.rglob("*.mp3")):
        if not path.is_file():
            continue
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            continue
        if rel.startswith(f"{COVERS_DIRNAME}/"):
            continue
        meta = index_by_file.get(rel, {})
        cover = meta.get("cover")
        cover_url = None
        if cover and (root / cover).is_file():
            cover_url = f"/api/library/cover/{cover}"
        results.append(
            {
                "filename": rel,
                "title": meta.get("title") or path.stem,
                "channel": meta.get("channel") or "",
                "duration": meta.get("duration"),
                "video_id": meta.get("video_id"),
                "cover": cover if cover_url else None,
                "cover_url": cover_url,
                "size": path.stat().st_size,
            }
        )
    return results


def resolve_safe_path(relpath: str, root: Path | None = None) -> Path:
    root = (root or get_download_dir()).resolve()
    # Decode may already be done by FastAPI; normalize separators
    cleaned = relpath.replace("\\", "/").lstrip("/")
    if ".." in cleaned.split("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    target = (root / cleaned).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Path escapes download dir") from exc
    return target


def stream_file_response(path: Path, request: Request) -> Response:
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    media = "audio/mpeg" if path.suffix.lower() == ".mp3" else "application/octet-stream"

    if not range_header:
        return FileResponse(
            path,
            media_type=media,
            headers={"Accept-Ranges": "bytes"},
        )

    units, _, range_spec = range_header.partition("=")
    if units.strip().lower() != "bytes":
        return FileResponse(path, media_type=media)

    start_str, _, end_str = range_spec.partition("-")
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1
    end = min(end, file_size - 1)
    if start < 0 or start >= file_size or end < start:
        raise HTTPException(status_code=416, detail="Invalid range")
    length = end - start + 1

    with path.open("rb") as fh:
        fh.seek(start)
        data = fh.read(length)

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Type": media,
    }
    return Response(content=data, status_code=206, headers=headers, media_type=media)


def download_cover(video_id: str, root: Path | None = None) -> str | None:
    """Fetch YouTube thumbnail into covers/{video_id}.jpg. Returns relative path or None."""
    if not video_id:
        return None
    root = root or get_download_dir()
    dest = covers_dir(root) / f"{video_id}.jpg"
    urls = [
        f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
    ]
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = resp.read()
            if data:
                dest.write_bytes(data)
                return f"{COVERS_DIRNAME}/{video_id}.jpg"
        except OSError:
            continue
    return None


def delete_track_file(relpath: str, root: Path | None = None) -> dict:
    """Delete MP3 (+ cover + index). Caller should also prune playlists."""
    root = root or get_download_dir()
    path = resolve_safe_path(relpath, root)
    if not path.is_file() or path.suffix.lower() != ".mp3":
        raise HTTPException(status_code=404, detail="MP3 not found")
    removed = remove_from_index(relpath, root)
    path.unlink(missing_ok=True)
    cover_rel = (removed or {}).get("cover")
    if cover_rel:
        cover_path = root / cover_rel
        if cover_path.is_file():
            cover_path.unlink(missing_ok=True)
    return {"deleted": relpath, "entry": removed}


def unique_filename(title: str, video_id: str, root: Path | None = None) -> str:
    """Pick %(title)s.mp3 or title [video_id].mp3 on collision with different id."""
    root = root or get_download_dir()
    safe = re.sub(r'[<>:"/\\|?*]', "_", title).strip() or video_id
    candidate = f"{safe}.mp3"
    path = root / candidate
    if not path.exists():
        return candidate
    existing = find_by_filename(candidate, root)
    if existing and existing.get("video_id") == video_id:
        return candidate
    return f"{safe} [{video_id}].mp3"
