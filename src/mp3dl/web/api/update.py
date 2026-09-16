"""Update check/install API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from mp3dl.update import check_update, install_update

router = APIRouter(prefix="/api/update", tags=["update"])


@router.get("/check")
def update_check():
    return check_update()


@router.post("/install")
def update_install():
    result = install_update()
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=result.get("error") or "Update failed")
    return result
