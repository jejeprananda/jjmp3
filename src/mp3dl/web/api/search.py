"""Search API with already-downloaded annotation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from mp3dl.search import search_youtube
from mp3dl.web.library import find_by_video_id

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search")
def search(q: str = Query(default="")):
    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query required")
    try:
        results = search_youtube(query)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    payload = []
    for r in results:
        existing = find_by_video_id(r.video_id)
        item = {
            "title": r.title,
            "channel": r.channel,
            "duration": r.duration,
            "video_id": r.video_id,
            "url": r.url,
            "downloaded": existing is not None,
            "filename": existing.get("filename") if existing else None,
            "cover": existing.get("cover") if existing else None,
        }
        if existing and existing.get("cover"):
            item["cover_url"] = f"/api/library/cover/{existing['cover']}"
        payload.append(item)
    return payload
