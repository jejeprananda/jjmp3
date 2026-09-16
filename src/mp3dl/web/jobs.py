"""Background download jobs for the web UI."""

from __future__ import annotations

import json
import subprocess
import threading
import uuid

from mp3dl.config import get_download_dir
from mp3dl.download import download_mp3_quiet
from mp3dl.web.library import (
    download_cover,
    find_by_video_id,
    find_by_title,
    unique_filename,
    upsert_index_entry,
)
from mp3dl.ytdlp import ytdlp_cmd

_LOCK = threading.Lock()
_JOBS: dict[str, dict] = {}


def _normalize_title(value: str | None) -> str:
    if not value:
        return ""
    lowered = str(value).strip().lower()
    # Same normalization as web.library (roughly), for job-level dedup.
    lowered = __import__("re").sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(lowered.split())


def _active_jobs() -> list[dict]:
    with _LOCK:
        return [dict(j) for j in _JOBS.values()]


def _active_job_by_video_id(video_id: str) -> dict | None:
    if not video_id:
        return None
    for job in _active_jobs():
        if (
            job.get("video_id") == video_id
            and job.get("status") in {"queued", "resolving", "downloading"}
        ):
            return job
    return None


def _active_job_by_title(title: str) -> dict | None:
    norm = _normalize_title(title)
    if not norm:
        return None
    for job in _active_jobs():
        if job.get("status") not in {"queued", "resolving", "downloading"}:
            continue
        if _normalize_title(job.get("title")) == norm:
            return job
    return None


def get_job(job_id: str) -> dict | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job else None


def _set_job(job_id: str, **fields) -> None:
    with _LOCK:
        if job_id in _JOBS:
            _JOBS[job_id].update(fields)


def extract_metadata(url: str) -> dict:
    proc = subprocess.run(
        ytdlp_cmd("-J", "--no-playlist", url),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "metadata extract failed").strip()
        raise RuntimeError(err[:500])
    data = json.loads(proc.stdout)
    video_id = data.get("id") or ""
    if not video_id:
        raise RuntimeError("No video id in metadata")
    return {
        "video_id": video_id,
        "title": data.get("title") or "(untitled)",
        "channel": data.get("uploader") or data.get("channel") or "",
        "duration": data.get("duration"),
        "url": data.get("webpage_url") or url,
    }


def start_download(
    *,
    url: str | None = None,
    video_id: str | None = None,
    title: str | None = None,
    channel: str | None = None,
    duration: int | None = None,
) -> dict:
    if video_id and not url:
        url = f"https://www.youtube.com/watch?v={video_id}"
    if not url:
        raise ValueError("url or video_id required")

    # 1) Already-downloaded by video_id (fast path)
    existing = find_by_video_id(video_id) if video_id else None
    if existing:
        return {
            "job_id": None,
            "status": "already_downloaded",
            "filename": existing["filename"],
            "track": existing,
        }

    # 2) Already-downloaded by title (user-facing dedup to prevent duplicates)
    if title:
        existing_by_title = find_by_title(title)
        if existing_by_title:
            return {
                "job_id": None,
                "status": "already_downloaded",
                "filename": existing_by_title["filename"],
                "track": existing_by_title,
            }

    # 3) Avoid concurrent duplicate downloads (same video_id or same title)
    if video_id:
        active = _active_job_by_video_id(video_id)
        if active:
            return active
    if title:
        active = _active_job_by_title(title)
        if active:
            return active

    job_id = uuid.uuid4().hex[:12]
    with _LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "progress": 0,
            "error": None,
            "filename": None,
            "video_id": video_id,
            "title": title,
            "channel": channel,
            "duration": duration,
            "url": url,
        }

    def _run() -> None:
        root = get_download_dir()
        try:
            _set_job(job_id, status="resolving", progress=1)
            meta = {
                "video_id": video_id or "",
                "title": title or "",
                "channel": channel or "",
                "duration": duration,
                "url": url,
            }
            if not meta["video_id"] or not meta["title"]:
                fetched = extract_metadata(url)
                meta = {**meta, **{k: v for k, v in fetched.items() if v}}

            if find_by_video_id(meta["video_id"], root):
                entry = find_by_video_id(meta["video_id"], root)
                _set_job(
                    job_id,
                    status="ready",
                    progress=100,
                    filename=entry["filename"],
                    video_id=meta["video_id"],
                    title=entry.get("title"),
                    channel=entry.get("channel"),
                )
                return

            # Title-based dedup (prevents duplicates even if video_id differs)
            if meta.get("title"):
                by_title = find_by_title(meta["title"], root)
                if by_title:
                    _set_job(
                        job_id,
                        status="ready",
                        progress=100,
                        filename=by_title["filename"],
                        video_id=meta["video_id"],
                        title=by_title.get("title"),
                        channel=by_title.get("channel"),
                    )
                    return

            filename = unique_filename(meta["title"], meta["video_id"], root)
            out_path = root / filename
            # yt-dlp template without extension; we force mp3
            template = str(out_path.with_suffix(".%(ext)s"))

            def on_progress(pct: float) -> None:
                _set_job(job_id, status="downloading", progress=min(pct, 99.0))

            _set_job(
                job_id,
                status="downloading",
                progress=5,
                video_id=meta["video_id"],
                title=meta["title"],
                channel=meta["channel"],
                duration=meta["duration"],
            )
            saved = download_mp3_quiet(meta["url"], root, output_template=template, on_progress=on_progress)
            # Normalize relative filename if yt-dlp picked a slightly different name
            try:
                rel = saved.resolve().relative_to(root.resolve()).as_posix()
            except ValueError:
                rel = filename
            cover = download_cover(meta["video_id"], root)
            entry = upsert_index_entry(
                video_id=meta["video_id"],
                filename=rel,
                title=meta["title"],
                channel=meta["channel"],
                duration=meta["duration"],
                cover=cover,
                root=root,
            )
            _set_job(
                job_id,
                status="ready",
                progress=100,
                filename=rel,
                video_id=meta["video_id"],
                title=entry.get("title"),
                channel=entry.get("channel"),
                cover=cover,
            )
        except Exception as exc:  # noqa: BLE001 — surface to client
            _set_job(job_id, status="error", error=str(exc)[:500], progress=0)

    threading.Thread(target=_run, daemon=True).start()
    return get_job(job_id) or {"job_id": job_id, "status": "queued"}
