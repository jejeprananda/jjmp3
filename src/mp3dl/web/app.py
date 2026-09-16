"""FastAPI application for JJMP3 local music player."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mp3dl.config import get_download_dir, get_web_port
from mp3dl.web import playlists_store
from mp3dl.web.api.download import router as download_router
from mp3dl.web.api.library import router as library_router
from mp3dl.web.api.lifecycle import router as lifecycle_router
from mp3dl.web.api.playlists import router as playlists_router
from mp3dl.web.api.search import router as search_router
from mp3dl.web.api.settings import router as settings_router

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    root = get_download_dir()
    root.mkdir(parents=True, exist_ok=True)
    playlists_store.load_playlists(root)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="JJMP3", lifespan=lifespan)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    app.include_router(search_router)
    app.include_router(download_router)
    app.include_router(library_router)
    app.include_router(playlists_router)
    app.include_router(settings_router)
    app.include_router(lifecycle_router)

    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


def run_web_server() -> None:
    from mp3dl.web.launcher import run_web_server as _run

    _run(open_browser=True)
