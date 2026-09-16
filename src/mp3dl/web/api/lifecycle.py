"""Lifecycle API — browser heartbeat and quit beacons."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from mp3dl.web import lifecycle

router = APIRouter(prefix="/api/lifecycle", tags=["lifecycle"])


class TabBody(BaseModel):
    tab_id: str


@router.post("/ping")
def ping(body: TabBody):
    lifecycle.ping_tab(body.tab_id.strip())
    return {"ok": True}


@router.post("/quit")
def quit_tab(body: TabBody):
    lifecycle.quit_tab(body.tab_id.strip())
    return {"ok": True}
