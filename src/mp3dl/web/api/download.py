"""Download API."""

from __future__ import annotations

import threading

from fastapi import APIRouter, HTTPException

from mp3dl.config import get_download_dir
from mp3dl.download import download_mp3
from mp3dl.web.models import get_track

router = APIRouter(prefix="/api", tags=["download"])

_DOWNLOADS: set[int] = set()
_LOCK = threading.Lock()


@router.post("/download/{track_id}")
def download_track(track_id: int):
    track = get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    with _LOCK:
        if track_id in _DOWNLOADS:
            return {"status": "already_running"}
        _DOWNLOADS.add(track_id)

    def _run() -> None:
        try:
            download_mp3(track.url, get_download_dir())
        finally:
            with _LOCK:
                _DOWNLOADS.discard(track_id)

    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started"}
