"""Stream and cache API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from mp3dl.web.models import get_track
from mp3dl.web.stream import (
    cache_path,
    cache_status,
    clear_cache,
    ensure_cached,
    stream_file_response,
)

router = APIRouter(prefix="/api", tags=["stream"])


@router.get("/stream/{track_id}/status")
def stream_status(track_id: int):
    track = get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    ensure_cached(track)
    return cache_status(track.video_id)


@router.get("/stream/{track_id}")
def stream_track(track_id: int, request: Request):
    track = get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    path = cache_path(track.video_id)
    if not path.is_file():
        ensure_cached(track)
        raise HTTPException(status_code=409, detail="Audio not ready yet")
    return stream_file_response(path, request)


@router.delete("/cache")
def delete_cache():
    removed = clear_cache()
    return {"removed": removed}
