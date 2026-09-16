"""Download API — permanent MP3 into download_dir."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mp3dl.web.jobs import get_job, start_download

router = APIRouter(prefix="/api/download", tags=["download"])


class DownloadBody(BaseModel):
    url: str | None = None
    video_id: str | None = None
    title: str | None = None
    channel: str | None = None
    duration: int | None = None


@router.post("")
def download(body: DownloadBody):
    if not body.url and not body.video_id:
        raise HTTPException(status_code=400, detail="url or video_id required")
    try:
        return start_download(
            url=body.url,
            video_id=body.video_id,
            title=body.title,
            channel=body.channel,
            duration=body.duration,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{job_id}")
def download_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
