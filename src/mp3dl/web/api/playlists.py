"""Playlist API backed by playlists.json in the download folder."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from mp3dl.web import playlists_store

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


class PlaylistCreate(BaseModel):
    name: str


class PlaylistRename(BaseModel):
    name: str


class TrackAdd(BaseModel):
    filename: str


class ReorderBody(BaseModel):
    tracks: list[str]


@router.get("")
def list_all():
    return playlists_store.list_playlists()


@router.get("/document")
def get_document():
    return playlists_store.load_playlists()


@router.put("/document")
def put_document(body: dict):
    return playlists_store.save_playlists(body)


@router.post("")
def create(body: PlaylistCreate):
    return playlists_store.create_playlist(body.name)


@router.get("/{playlist_id}")
def get_one(playlist_id: str):
    pl = playlists_store.get_playlist(playlist_id)
    if pl is None:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return pl


@router.put("/{playlist_id}")
def rename(playlist_id: str, body: PlaylistRename):
    return playlists_store.rename_playlist(playlist_id, body.name)


@router.delete("/{playlist_id}")
def remove(playlist_id: str):
    playlists_store.delete_playlist(playlist_id)
    return {"ok": True}


@router.post("/{playlist_id}/tracks")
def add_track(playlist_id: str, body: TrackAdd):
    if not body.filename.strip():
        raise HTTPException(status_code=400, detail="filename required")
    return playlists_store.add_track_to_playlist(playlist_id, body.filename.strip())


@router.delete("/{playlist_id}/tracks")
def remove_track(playlist_id: str, filename: str = Query(...)):
    return playlists_store.remove_track_from_playlist(playlist_id, filename)


@router.put("/{playlist_id}/tracks")
def reorder(playlist_id: str, body: ReorderBody):
    return playlists_store.set_playlist_tracks(playlist_id, body.tracks)
