"""FastAPI application for JJMP3 Web UI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mp3dl.config import get_db_path, get_web_port
from mp3dl.web.api.download import router as download_router
from mp3dl.web.api.import_playlist import router as import_router
from mp3dl.web.api.playlists import router as playlists_router
from mp3dl.web.api.queue import router as queue_router
from mp3dl.web.api.search import router as search_router
from mp3dl.web.api.stream import router as stream_router
from mp3dl.web.api.tracks import router as tracks_router
from mp3dl.web.models import init_db

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(get_db_path())
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="JJMP3 Web", lifespan=lifespan)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    app.include_router(search_router)
    app.include_router(tracks_router)
    app.include_router(playlists_router)
    app.include_router(queue_router)
    app.include_router(stream_router)
    app.include_router(import_router)
    app.include_router(download_router)

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


def run_web_server() -> None:
    import webbrowser

    import uvicorn

    port = get_web_port()
    webbrowser.open(f"http://127.0.0.1:{port}")
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="info")
