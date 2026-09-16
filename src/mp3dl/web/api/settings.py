"""Settings API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mp3dl.config import get_download_dir, get_web_port, set_download_dir
from mp3dl.update import get_local_version
from mp3dl.web import playlists_store

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    download_dir: str


@router.get("")
def get_settings():
    root = get_download_dir()
    playlists_store.load_playlists(root)  # ensure playlists.json exists
    return {
        "download_dir": str(root),
        "web_port": get_web_port(),
        "version": get_local_version(),
    }


@router.put("")
def update_settings(body: SettingsUpdate):
    path = body.download_dir.strip()
    if not path:
        raise HTTPException(status_code=400, detail="download_dir required")
    try:
        resolved = set_download_dir(path)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    playlists_store.load_playlists(resolved)
    return {
        "download_dir": str(resolved),
        "web_port": get_web_port(),
        "version": get_local_version(),
    }
