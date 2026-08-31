"""yt-dlp audio cache and HTTP Range streaming."""

from __future__ import annotations

import re
import subprocess
import threading
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, Response

from mp3dl.config import get_cache_dir
from mp3dl.web.models import Track
from mp3dl.ytdlp import ytdlp_cmd

_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)%")
_LOCK = threading.Lock()
_DOWNLOADS: dict[str, dict] = {}
_FAILURES: dict[str, str] = {}


def cache_path(video_id: str) -> Path:
    return get_cache_dir() / f"{video_id}.mp3"


def cache_status(video_id: str) -> dict:
    path = cache_path(video_id)
    with _LOCK:
        active = _DOWNLOADS.get(video_id)
        failure = _FAILURES.get(video_id)
    if path.is_file() and path.stat().st_size > 0:
        return {"ready": True, "progress": 100, "cached": True, "error": None}
    if failure:
        return {
            "ready": False,
            "progress": 0,
            "cached": False,
            "error": failure,
        }
    if active:
        return {
            "ready": False,
            "progress": active.get("progress", 0),
            "cached": False,
            "error": active.get("error"),
        }
    return {"ready": False, "progress": 0, "cached": False, "error": None}


def ensure_cached(track: Track) -> None:
    path = cache_path(track.video_id)
    if path.is_file() and path.stat().st_size > 0:
        return
    with _LOCK:
        if track.video_id in _DOWNLOADS or track.video_id in _FAILURES:
            return
        _DOWNLOADS[track.video_id] = {"progress": 0, "proc": None, "error": None}

    def _run() -> None:
        output_template = str(path.with_suffix(".%(ext)s"))
        cmd = ytdlp_cmd(
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",
            "--newline",
            "--progress",
            "-o",
            output_template,
            track.url,
        )
        tail: list[str] = []
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            with _LOCK:
                _DOWNLOADS[track.video_id]["proc"] = proc
            assert proc.stdout is not None
            for raw in proc.stdout:
                tail.append(raw)
                if len(tail) > 20:
                    tail.pop(0)
                match = _PERCENT_RE.search(raw)
                if match:
                    with _LOCK:
                        _DOWNLOADS[track.video_id]["progress"] = min(
                            float(match.group(1)), 99.0
                        )
            proc.wait()
            if proc.returncode != 0 and not (path.is_file() and path.stat().st_size > 0):
                err = "".join(tail).strip() or f"yt-dlp exit code {proc.returncode}"
                if "ERROR:" in err:
                    err = err[err.rfind("ERROR:") :].strip()
                with _LOCK:
                    _FAILURES[track.video_id] = err[:500]
            else:
                with _LOCK:
                    _DOWNLOADS[track.video_id]["progress"] = 100
        except FileNotFoundError:
            with _LOCK:
                _FAILURES[track.video_id] = "yt-dlp tidak ditemukan"
        except OSError as exc:
            with _LOCK:
                _FAILURES[track.video_id] = str(exc)[:500]
        finally:
            with _LOCK:
                _DOWNLOADS.pop(track.video_id, None)

    threading.Thread(target=_run, daemon=True).start()


def stream_file_response(path: Path, request: Request) -> Response:
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio not ready")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")

    if not range_header:
        return FileResponse(
            path,
            media_type="audio/mpeg",
            headers={"Accept-Ranges": "bytes"},
        )

    units, _, range_spec = range_header.partition("=")
    if units.strip().lower() != "bytes":
        return FileResponse(path, media_type="audio/mpeg")

    start_str, _, end_str = range_spec.partition("-")
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1
    end = min(end, file_size - 1)
    length = end - start + 1

    with path.open("rb") as fh:
        fh.seek(start)
        data = fh.read(length)

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Content-Type": "audio/mpeg",
    }
    return Response(content=data, status_code=206, headers=headers, media_type="audio/mpeg")


def clear_cache() -> int:
    cache_dir = get_cache_dir()
    removed = 0
    for path in cache_dir.glob("*.mp3"):
        path.unlink(missing_ok=True)
        removed += 1
    with _LOCK:
        _FAILURES.clear()
    return removed


def clear_failure(video_id: str) -> None:
    with _LOCK:
        _FAILURES.pop(video_id, None)
