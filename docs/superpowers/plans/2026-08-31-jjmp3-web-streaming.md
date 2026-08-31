# JJMP3 Web Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local Web UI (`jjmp3 web`) for streaming YouTube audio, managing multi-playlists, queue, and history — while keeping the existing CLI downloader.

**Architecture:** FastAPI monolith binds to `127.0.0.1`, serves REST API + vanilla JS static SPA. SQLite at `~/.config/jjmp3/jjmp3.db` for playlists/queue/history. Audio cached to `~/.cache/jjmp3/{video_id}.mp3` and served with HTTP Range support for seek.

**Tech Stack:** Python 3.10+, FastAPI, uvicorn, stdlib sqlite3, yt-dlp, ffmpeg, vanilla JS/HTML/CSS

## Global Constraints

- Bind web server to `127.0.0.1` only (not `0.0.0.0`)
- Default `web_port`: 8765
- Default `cache_dir`: `~/.cache/jjmp3`
- Default `cache_max_age_days`: 7
- Accent colors: cyan `#22D3EE`, magenta `#E879F9`, pink `#F472B6`
- UI: YouTube Music layout, white/light theme
- Keep existing `jjmp3` CLI behavior unchanged
- Reuse `search.py`, `download.py` where possible
- No auth, no LAN/internet deployment in v1
- Desktop-first (≥1024px); mobile out of scope v1

---

## File Map

| File | Responsibility |
|------|----------------|
| `pyproject.toml` | Add fastapi, uvicorn, pytest deps |
| `src/mp3dl/config.py` | Extend with web_port, cache_dir, cache_max_age_days, db_path |
| `src/mp3dl/cli.py` | Add `web` subcommand via argparse |
| `src/mp3dl/web/models.py` | SQLite schema init + CRUD |
| `src/mp3dl/web/stream.py` | yt-dlp cache fetch + Range file serve |
| `src/mp3dl/web/app.py` | FastAPI app factory, router mount, static files |
| `src/mp3dl/web/api/*.py` | Route handlers per domain |
| `src/mp3dl/web/static/` | SPA: index.html, css, js |
| `tests/test_models.py` | SQLite CRUD unit tests |
| `tests/test_api.py` | FastAPI TestClient integration tests |

---

### Task 1: Dependencies & Config Extensions

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/mp3dl/config.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: `get_web_port() -> int`, `get_cache_dir() -> Path`, `get_cache_max_age_days() -> int`, `get_db_path() -> Path`

- [ ] **Step 1: Add dependencies to pyproject.toml**

Add to `[project] dependencies`:

```toml
"fastapi>=0.115",
"uvicorn[standard]>=0.32",
```

Add dev optional or `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "httpx>=0.27"]
```

- [ ] **Step 2: Extend config.py**

```python
DEFAULT_WEB_PORT = 8765
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "jjmp3"
DEFAULT_CACHE_MAX_AGE_DAYS = 7
DB_PATH = CONFIG_DIR / "jjmp3.db"

def get_web_port() -> int:
    raw = load_config().get("web_port")
    if isinstance(raw, int) and 1024 <= raw <= 65535:
        return raw
    if isinstance(raw, str) and raw.isdigit():
        val = int(raw)
        if 1024 <= val <= 65535:
            return val
    return DEFAULT_WEB_PORT

def get_cache_dir() -> Path:
    raw = load_config().get("cache_dir")
    if isinstance(raw, str) and raw.strip():
        path = Path(raw).expanduser().resolve()
    else:
        path = DEFAULT_CACHE_DIR.resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_cache_max_age_days() -> int:
    raw = load_config().get("cache_max_age_days")
    if isinstance(raw, int) and raw > 0:
        return raw
    return DEFAULT_CACHE_MAX_AGE_DAYS

def get_db_path() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return DB_PATH
```

- [ ] **Step 3: Write failing config test**

Create `tests/test_config.py`:

```python
from mp3dl.config import DEFAULT_WEB_PORT, get_web_port, get_cache_dir

def test_get_web_port_default():
    assert get_web_port() == DEFAULT_WEB_PORT

def test_get_cache_dir_creates_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # reload or patch CONFIG - use monkeypatch on load_config returning {}
    from mp3dl import config
    monkeypatch.setattr(config, "load_config", lambda: {})
    monkeypatch.setattr(config, "DEFAULT_CACHE_DIR", tmp_path / ".cache" / "jjmp3")
    path = config.get_cache_dir()
    assert path.is_dir()
```

- [ ] **Step 4: Run tests**

Run: `pip install -e ".[dev]" && pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/mp3dl/config.py tests/
git commit -m "feat: add web config helpers and test dependencies"
```

---

### Task 2: SQLite Models

**Files:**
- Create: `src/mp3dl/web/__init__.py`
- Create: `src/mp3dl/web/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces:
  - `init_db(db_path: Path) -> None`
  - `get_connection() -> sqlite3.Connection`
  - `Track`, `Playlist` dataclasses
  - `create_playlist(name: str) -> int`
  - `list_playlists() -> list[Playlist]`
  - `upsert_track(video_id, title, channel, duration, url, thumbnail) -> int`
  - `get_track(track_id: int) -> Track | None`
  - `get_track_by_video_id(video_id: str) -> Track | None`
  - `add_track_to_playlist(playlist_id, track_id) -> None`
  - `list_playlist_tracks(playlist_id) -> list[Track]`
  - `reorder_playlist_tracks(playlist_id, track_ids: list[int]) -> None`
  - `list_queue() -> list[tuple[int, Track]]`  # (queue_row_id, track)
  - `add_to_queue(track_id) -> int`
  - `clear_queue() -> None`
  - `reorder_queue(queue_ids: list[int]) -> None`
  - `log_history(track_id) -> None`
  - `list_history(limit: int = 50) -> list[Track]`

- [ ] **Step 1: Write failing model tests**

```python
import pytest
from pathlib import Path
from mp3dl.web.models import init_db, create_playlist, list_playlists, upsert_track, get_track

@pytest.fixture
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("mp3dl.web.models.get_db_path", lambda: db_path)
    init_db(db_path)
    return db_path

def test_create_and_list_playlist(db):
    pid = create_playlist("Favorit")
    playlists = list_playlists()
    assert len(playlists) == 1
    assert playlists[0].name == "Favorit"

def test_upsert_track_dedup(db):
    id1 = upsert_track("abc123", "Song", "Artist", 180, "https://youtube.com/watch?v=abc123", None)
    id2 = upsert_track("abc123", "Song Updated", "Artist", 180, "https://youtube.com/watch?v=abc123", None)
    assert id1 == id2
    assert get_track(id1).title == "Song Updated"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement models.py**

Implement schema from spec section 5 with WAL mode, foreign keys ON, and all CRUD functions. Use `@dataclass` for `Track` and `Playlist`. Module-level connection uses `get_db_path()` from config.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/mp3dl/web/ tests/test_models.py
git commit -m "feat: add SQLite models for playlists, tracks, queue, history"
```

---

### Task 3: FastAPI App Skeleton & `jjmp3 web`

**Files:**
- Create: `src/mp3dl/web/app.py`
- Create: `src/mp3dl/web/static/index.html` (placeholder)
- Modify: `src/mp3dl/cli.py`
- Modify: `pyproject.toml` (optional second entry point not needed — use argparse subcommand)

**Interfaces:**
- Produces: `create_app() -> FastAPI`, `run_web_server() -> None`
- CLI: `jjmp3 web` starts uvicorn on `127.0.0.1:{port}`, opens browser

- [ ] **Step 1: Write failing API health test**

Create `tests/test_api.py`:

```python
from fastapi.testclient import TestClient
from mp3dl.web.app import create_app

def test_health():
    client = TestClient(create_app())
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/test_api.py::test_health -v`

- [ ] **Step 3: Implement app.py**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from mp3dl.web.models import init_db
from mp3dl.config import get_db_path, get_web_port

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
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app

def run_web_server() -> None:
    import webbrowser
    import uvicorn
    port = get_web_port()
    webbrowser.open(f"http://127.0.0.1:{port}")
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="info")
```

- [ ] **Step 4: Add `web` subcommand to cli.py**

Use `argparse` — if `sys.argv[1] == "web"`, call `run_web_server()` and return 0. Otherwise existing `main()` flow.

Update `[project.scripts]` is NOT needed; handle in `main()`:

```python
def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        from mp3dl.web.app import run_web_server
        run_web_server()
        return 0
    ...
```

- [ ] **Step 5: Run test — expect PASS**

Run: `pytest tests/test_api.py::test_health -v`

- [ ] **Step 6: Commit**

```bash
git add src/mp3dl/web/app.py src/mp3dl/cli.py src/mp3dl/web/static/index.html tests/test_api.py
git commit -m "feat: add FastAPI skeleton and jjmp3 web command"
```

---

### Task 4: Search & Tracks API

**Files:**
- Create: `src/mp3dl/web/api/__init__.py`
- Create: `src/mp3dl/web/api/search.py`
- Create: `src/mp3dl/web/api/tracks.py`
- Modify: `src/mp3dl/web/app.py`

**Interfaces:**
- `GET /api/search?q=` → `list[SearchResult]` JSON (reuse `search_youtube`)
- `POST /api/tracks` body `{ "url": str }` → track JSON (yt-dlp metadata extract + upsert)

- [ ] **Step 1: Write failing search test**

```python
def test_search_requires_query(client):
    r = client.get("/api/search")
    assert r.status_code == 422

def test_search_empty_query(client):
    r = client.get("/api/search?q=")
    assert r.status_code == 400
```

- [ ] **Step 2: Implement search router** — wrap `search_youtube(q)`, return JSON list

- [ ] **Step 3: Implement tracks router** — `yt-dlp -J --no-playlist URL` → parse → `upsert_track`

- [ ] **Step 4: Mount routers in app.py**

- [ ] **Step 5: Run tests, commit**

```bash
git commit -m "feat: add search and track creation API"
```

---

### Task 5: Audio Streaming (Cache + Range)

**Files:**
- Create: `src/mp3dl/web/stream.py`
- Create: `src/mp3dl/web/api/stream.py`
- Modify: `src/mp3dl/web/app.py`

**Interfaces:**
- Produces:
  - `cache_path(video_id: str) -> Path`
  - `ensure_cached(track: Track) -> None`  # starts background yt-dlp if missing
  - `cache_status(video_id: str) -> dict`  # `{ready, progress, cached}`
  - `stream_file_response(path: Path, request: Request) -> Response`  # Range support
- Endpoints:
  - `GET /api/stream/{track_id}/status`
  - `GET /api/stream/{track_id}`
  - `DELETE /api/cache`

- [ ] **Step 1: Implement stream.py**

Use subprocess to run:

```python
["yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
 "-o", str(cache_path), track.url]
```

Track in-progress downloads in a module dict `{video_id: {"progress": float, "proc": Popen}}`.
Parse stdout for `%` like `download.py`.

For Range serving, use `FileResponse` with `headers={"Accept-Ranges": "bytes"}` or implement manual Range parsing from `Request.headers.get("range")`.

- [ ] **Step 2: Write test for status endpoint (cached file exists)**

```python
def test_stream_status_cached(client, db, tmp_path, monkeypatch):
    # create track, write fake mp3 to cache, assert ready=True
    ...
```

- [ ] **Step 3: Wire API routes**

- [ ] **Step 4: Manual test** — `jjmp3 web`, play track, verify seek works

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add audio cache streaming with HTTP Range support"
```

---

### Task 6: Playlists API

**Files:**
- Create: `src/mp3dl/web/api/playlists.py`
- Modify: `src/mp3dl/web/app.py`
- Extend: `tests/test_api.py`

**Endpoints:** full CRUD per spec section 6.

- [ ] **Step 1: Write tests for playlist CRUD + reorder**

- [ ] **Step 2: Implement router using models.py functions**

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat: add playlists REST API"
```

---

### Task 7: Queue & History API

**Files:**
- Create: `src/mp3dl/web/api/queue.py`
- Create: `src/mp3dl/web/api/history.py`

**Endpoints:**
- Queue: GET, POST `{track_id}` or `{playlist_id}`, DELETE, PUT reorder, DELETE clear
- History: GET paginated; POST called internally on track end (also expose POST for frontend)

- [ ] **Step 1: Write queue/history tests**

- [ ] **Step 2: Implement routers**

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat: add queue and history REST API"
```

---

### Task 8: YouTube Playlist Import & Download API

**Files:**
- Create: `src/mp3dl/web/api/import_playlist.py`
- Create: `src/mp3dl/web/api/download.py`

**Interfaces:**
- `POST /api/import/youtube-playlist` — reuse pattern from `search.py` with `--flat-playlist -J`
- `POST /api/download/{track_id}` — call `download_mp3(track.url, get_download_dir())` in background thread, return `{status: "started"}`

- [ ] **Step 1: Implement import endpoint with bulk upsert**

- [ ] **Step 2: Implement download endpoint**

- [ ] **Step 3: Test import with mocked yt-dlp output**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add YouTube playlist import and download API"
```

---

### Task 9: Frontend Foundation (Layout + Theme)

**Files:**
- Create: `src/mp3dl/web/static/index.html`
- Create: `src/mp3dl/web/static/css/app.css`
- Create: `src/mp3dl/web/static/js/api.js`

**Interfaces:**
- `api.js` exports: `search(q)`, `getPlaylists()`, `createPlaylist(name)`, etc.

- [ ] **Step 1: Build HTML skeleton** — 3-zone layout per spec section 7

```html
<!-- sidebar, main, player-bar -->
<div id="app">
  <header class="topbar">...</header>
  <div class="body">
    <nav id="sidebar">...</nav>
    <main id="main">...</main>
  </div>
  <footer id="player">...</footer>
</div>
```

- [ ] **Step 2: CSS with design tokens**

```css
:root {
  --bg-primary: #FFFFFF;
  --accent-cyan: #22D3EE;
  --accent-magenta: #E879F9;
  /* ... all tokens from spec */
}
```

- [ ] **Step 3: api.js fetch wrapper**

```javascript
const API = "/api";
export async function search(q) {
  const r = await fetch(`${API}/search?q=${encodeURIComponent(q)}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
```

- [ ] **Step 4: Manual verify** — page loads at `http://127.0.0.1:8765`

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add web UI shell with YT Music light theme"
```

---

### Task 10: Player Component

**Files:**
- Create: `src/mp3dl/web/static/js/player.js`
- Modify: `src/mp3dl/web/static/js/app.js`

**Interfaces:**
- `Player` class: `play(track)`, `pause()`, `next()`, `prev()`, `setShuffle()`, `setRepeat()`, `onEnded(callback)`
- Polls `/api/stream/{id}/status` until ready, sets `<audio src="/api/stream/{id}">`

- [ ] **Step 1: Implement Player with HTML5 Audio**

```javascript
export class Player {
  constructor(audioEl) {
    this.audio = audioEl;
    this.repeat = "off"; // off | one | all
    this.shuffle = false;
    this.queue = [];
    this.queueIndex = -1;
  }
  async playTrack(track) {
    const status = await pollUntilReady(track.id);
    this.audio.src = `/api/stream/${track.id}`;
    await this.audio.play();
  }
}
```

- [ ] **Step 2: Wire player bar controls** — play/pause, seek, volume, shuffle, repeat cycle

- [ ] **Step 3: On ended** — POST history, call playNext()

- [ ] **Step 4: Manual test full playback flow**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add web audio player with shuffle and repeat"
```

---

### Task 11: Playlist & Search UI

**Files:**
- Create: `src/mp3dl/web/static/js/playlists.js`
- Modify: `src/mp3dl/web/static/js/app.js`

- [ ] **Step 1: Search view** — debounced search input → results list → click to play / add to playlist menu

- [ ] **Step 2: Sidebar playlist list** — create, rename, delete, select to view tracks

- [ ] **Step 3: Playlist track list** — render rows with thumbnail, duration, context menu

- [ ] **Step 4: Paste URL dialog** — prompt for URL → POST /api/tracks → add to playlist

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add search and playlist management UI"
```

---

### Task 12: Queue, History & Drag-Drop

**Files:**
- Modify: `src/mp3dl/web/static/js/app.js`
- Modify: `src/mp3dl/web/static/js/playlists.js`

- [ ] **Step 1: Queue view** — list, remove, clear, play playlist populates queue

- [ ] **Step 2: History view** — list recent, click to replay

- [ ] **Step 3: Drag-and-drop reorder** — HTML5 DnD on track rows, PUT reorder endpoints

- [ ] **Step 4: Context menu (⋮)** — Play, Play next, Add to playlist, Download, Remove

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add queue, history, and drag-drop reorder"
```

---

### Task 13: Import Playlist & Settings Panel

**Files:**
- Modify: `src/mp3dl/web/static/js/app.js`
- Modify: `src/mp3dl/web/static/index.html`

- [ ] **Step 1: Import YouTube playlist modal** — URL input + target playlist select

- [ ] **Step 2: Settings panel (⚙)** — show download dir, cache clear button (`DELETE /api/cache`)

- [ ] **Step 3: Download button in player + context menu**

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add playlist import, settings, and download in web UI"
```

---

### Task 14: README & Final Integration

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document `jjmp3 web` usage, new deps, features**

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -v`

- [ ] **Step 3: Manual smoke test checklist**

- [ ] `jjmp3` CLI still works
- [ ] `jjmp3 web` opens browser
- [ ] Search → play → seek
- [ ] Create playlist, add tracks, reorder
- [ ] Import YT playlist
- [ ] Queue shuffle/repeat
- [ ] History logs plays
- [ ] Download from web UI

- [ ] **Step 4: Commit**

```bash
git commit -m "docs: document JJMP3 web streaming features"
```

---

## Plan Self-Review

**Spec coverage:**
- FastAPI monolith + vanilla JS → Tasks 3, 9
- Dual entry `jjmp3` + `jjmp3 web` → Task 3
- Local-only 127.0.0.1 → Task 3
- Search + paste URL + import → Tasks 4, 8, 11, 13
- Stream + download → Tasks 5, 8, 10, 13
- Multi-playlist + queue + history + drag-drop → Tasks 6, 7, 11, 12
- Full playback controls → Task 10
- YT Music white theme + JJMP3 accents → Task 9
- Cache + Range seek → Task 5
- Error handling → embedded in each API task
- Security local-only → Task 3

**No gaps identified.**

**Placeholder scan:** No TBD/TODO entries.

**Type consistency:** Track/Playlist dataclasses defined in Task 2, used throughout API and frontend JSON shape `{id, video_id, title, channel, duration, url, thumbnail}`.
