"""Search API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from mp3dl.search import search_youtube

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
    return [
        {
            "title": r.title,
            "channel": r.channel,
            "duration": r.duration,
            "video_id": r.video_id,
            "url": r.url,
        }
        for r in results
    ]
