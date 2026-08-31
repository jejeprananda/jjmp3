"""Queue and history API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mp3dl.web.models import (
    add_playlist_to_queue,
    add_to_queue,
    clear_queue,
    get_track,
    list_history,
    list_queue,
    log_history,
    remove_from_queue,
    reorder_queue,
    track_to_dict,
)

router = APIRouter(prefix="/api", tags=["queue"])


class QueueAdd(BaseModel):
    track_id: int | None = None
    playlist_id: int | None = None


class QueueReorder(BaseModel):
    queue_ids: list[int]


class HistoryAdd(BaseModel):
    track_id: int


@router.get("/queue")
def get_queue():
    return [
        {
            "id": item.id,
            "position": item.position,
            "added_at": item.added_at,
            "track": track_to_dict(item.track),
        }
        for item in list_queue()
    ]


@router.post("/queue")
def post_queue(body: QueueAdd):
    if body.playlist_id is not None:
        count = add_playlist_to_queue(body.playlist_id)
        return {"added": count}
    if body.track_id is None:
        raise HTTPException(status_code=400, detail="track_id or playlist_id required")
    if get_track(body.track_id) is None:
        raise HTTPException(status_code=404, detail="Track not found")
    qid = add_to_queue(body.track_id)
    return {"id": qid}


@router.delete("/queue/{queue_id}")
def delete_queue_item(queue_id: int):
    if not remove_from_queue(queue_id):
        raise HTTPException(status_code=404, detail="Queue item not found")
    return {"ok": True}


@router.put("/queue/reorder")
def put_queue_reorder(body: QueueReorder):
    reorder_queue(body.queue_ids)
    return {"ok": True}


@router.delete("/queue")
def delete_queue():
    clear_queue()
    return {"ok": True}


@router.get("/history")
def get_history(limit: int = 50):
    return [track_to_dict(t) for t in list_history(limit)]


@router.post("/history")
def post_history(body: HistoryAdd):
    if get_track(body.track_id) is None:
        raise HTTPException(status_code=404, detail="Track not found")
    log_history(body.track_id)
    return {"ok": True}
