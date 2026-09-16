"""Library API — scan, stream, delete local MP3s."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from mp3dl.config import get_download_dir
from mp3dl.web import playlists_store
from mp3dl.web.library import (
    delete_track_file,
    resolve_safe_path,
    scan_library,
    stream_file_response,
)

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("")
def list_library():
    root = get_download_dir()
    return {
        "download_dir": str(root),
        "tracks": scan_library(root),
    }


@router.get("/file/{relpath:path}")
def get_file(relpath: str, request: Request):
    path = resolve_safe_path(relpath)
    if path.suffix.lower() != ".mp3":
        raise HTTPException(status_code=400, detail="Only MP3 files can be streamed")
    return stream_file_response(path, request)


@router.get("/cover/{relpath:path}")
def get_cover(relpath: str):
    path = resolve_safe_path(relpath)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Cover not found")
    suffix = path.suffix.lower()
    media = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    return FileResponse(path, media_type=media)


@router.delete("/file/{relpath:path}")
def delete_file(relpath: str):
    result = delete_track_file(relpath)
    playlists_store.prune_filename_from_all(relpath)
    return result
