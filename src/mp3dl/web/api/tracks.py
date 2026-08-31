"""Track creation API."""

from __future__ import annotations

import json
import subprocess

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mp3dl.web.models import track_to_dict, upsert_track

router = APIRouter(prefix="/api", tags=["tracks"])


class TrackCreate(BaseModel):
    url: str


def _extract_metadata(url: str) -> dict:
    proc = subprocess.run(
        ["yt-dlp", "-J", "--no-playlist", url.strip()],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "yt-dlp failed").strip()
        raise HTTPException(status_code=400, detail=err)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Invalid yt-dlp output") from exc
    video_id = data.get("id") or ""
    if not video_id:
        raise HTTPException(status_code=400, detail="Could not resolve video ID")
    return {
        "video_id": video_id,
        "title": data.get("title") or "(untitled)",
        "channel": data.get("uploader") or data.get("channel") or "",
        "duration": data.get("duration"),
        "url": data.get("webpage_url") or url,
        "thumbnail": data.get("thumbnail"),
    }


@router.post("/tracks")
def create_track(body: TrackCreate):
    meta = _extract_metadata(body.url)
    track_id = upsert_track(
        meta["video_id"],
        meta["title"],
        meta["channel"],
        meta["duration"],
        meta["url"],
        meta["thumbnail"],
    )
    from mp3dl.web.models import get_track

    track = get_track(track_id)
    if track is None:
        raise HTTPException(status_code=500, detail="Track not found after insert")
    return track_to_dict(track)
