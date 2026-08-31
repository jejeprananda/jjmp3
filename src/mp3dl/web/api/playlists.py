"""Playlist API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mp3dl.web.models import (
    add_track_to_playlist,
    create_playlist,
    delete_playlist,
    get_playlist,
    get_track,
    list_playlist_tracks,
    list_playlists,
    playlist_to_dict,
    remove_track_from_playlist,
    rename_playlist,
    reorder_playlist_tracks,
    track_to_dict,
)

router = APIRouter(prefix="/api", tags=["playlists"])


class PlaylistCreate(BaseModel):
    name: str


class PlaylistRename(BaseModel):
    name: str


class TrackAdd(BaseModel):
    track_id: int


class ReorderBody(BaseModel):
    track_ids: list[int]


@router.get("/playlists")
def get_playlists():
    return [playlist_to_dict(p) for p in list_playlists()]


@router.post("/playlists")
def post_playlist(body: PlaylistCreate):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    pid = create_playlist(name)
    playlist = get_playlist(pid)
    assert playlist is not None
    return playlist_to_dict(playlist)


@router.put("/playlists/{playlist_id}")
def put_playlist(playlist_id: int, body: PlaylistRename):
    if not rename_playlist(playlist_id, body.name):
        raise HTTPException(status_code=404, detail="Playlist not found")
    playlist = get_playlist(playlist_id)
    assert playlist is not None
    return playlist_to_dict(playlist)


@router.delete("/playlists/{playlist_id}")
def delete_playlist_route(playlist_id: int):
    if not delete_playlist(playlist_id):
        raise HTTPException(status_code=404, detail="Playlist not found")
    return {"ok": True}


@router.get("/playlists/{playlist_id}/tracks")
def get_playlist_tracks(playlist_id: int):
    if get_playlist(playlist_id) is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return [track_to_dict(t) for t in list_playlist_tracks(playlist_id)]


@router.post("/playlists/{playlist_id}/tracks")
def post_playlist_track(playlist_id: int, body: TrackAdd):
    if get_playlist(playlist_id) is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    if get_track(body.track_id) is None:
        raise HTTPException(status_code=404, detail="Track not found")
    add_track_to_playlist(playlist_id, body.track_id)
    return {"ok": True}


@router.delete("/playlists/{playlist_id}/tracks/{track_id}")
def delete_playlist_track(playlist_id: int, track_id: int):
    if not remove_track_from_playlist(playlist_id, track_id):
        raise HTTPException(status_code=404, detail="Track not in playlist")
    return {"ok": True}


@router.put("/playlists/{playlist_id}/tracks/reorder")
def reorder_playlist(playlist_id: int, body: ReorderBody):
    if get_playlist(playlist_id) is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    reorder_playlist_tracks(playlist_id, body.track_ids)
    return {"ok": True}
