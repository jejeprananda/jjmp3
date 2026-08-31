"""YouTube playlist import API."""

from __future__ import annotations

import json
import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mp3dl.web.models import add_track_to_playlist, get_playlist, upsert_track
from mp3dl.ytdlp import ytdlp_cmd

router = APIRouter(prefix="/api", tags=["import"])


class ImportBody(BaseModel):
    url: str
    playlist_id: int


@router.post("/import/youtube-playlist")
def import_youtube_playlist(body: ImportBody):
    if get_playlist(body.playlist_id) is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    proc = subprocess.run(
        ytdlp_cmd("--flat-playlist", "-J", body.url.strip()),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "import failed").strip()
        raise HTTPException(status_code=400, detail=err)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Invalid yt-dlp output") from exc

    entries = payload.get("entries") or []
    added = 0
    for entry in entries:
        if not entry:
            continue
        video_id = entry.get("id") or ""
        if not video_id:
            continue
        url = entry.get("url") or entry.get("webpage_url")
        if not url:
            url = f"https://www.youtube.com/watch?v={video_id}"
        track_id = upsert_track(
            video_id,
            entry.get("title") or "(untitled)",
            entry.get("uploader") or entry.get("channel") or "",
            entry.get("duration"),
            url,
            entry.get("thumbnail"),
        )
        add_track_to_playlist(body.playlist_id, track_id)
        added += 1
    return {"added": added}
