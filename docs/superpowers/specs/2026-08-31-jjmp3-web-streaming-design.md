# JJMP3 Web Streaming — Design Spec

**Date:** 2026-08-31  
**Status:** Approved  
**Author:** Brainstorming session

---

## 1. Overview

Extend JJMP3 from a CLI YouTube-to-MP3 downloader into a **local Web UI music player** with streaming, multi-playlist management, queue, history, and download — while keeping the existing CLI intact.

### Goals

- Stream audio per track in the browser without permanent download
- Create and manage multiple playlists
- Add tracks via search, paste URL, or import YouTube playlist
- Full playback controls (shuffle, repeat, queue, drag-drop reorder, history)
- Keep existing MP3 download feature
- Dual entry: `jjmp3` (CLI) + `jjmp3 web` (Web UI)

### Non-Goals (v1)

- Multi-user / authentication
- LAN or internet deployment
- Mobile-first responsive design
- React/Vite SPA (vanilla JS only)

---

## 2. Requirements Summary

| Aspect | Decision |
|--------|----------|
| Interface | Web UI in browser |
| Access | Local-only (`localhost`), single user, no login |
| Track input | Search + paste URL + import YouTube playlist |
| Download | Retained alongside streaming |
| Entry point | `jjmp3` (CLI) + `jjmp3 web` (Web UI) |
| Playback | Full — shuffle, repeat (off/one/all), volume, queue, history, drag-drop |
| Visual | YouTube Music layout, white/light theme |
| Accent | Cyan/magenta JJMP3 brand (from existing CLI) |

---

## 3. Architecture

### Approach: FastAPI Monolith + Vanilla JS

Single Python process: FastAPI serves REST API + static frontend. SQLite for persistent data. Audio served via cached files with HTTP Range support.

**Rejected alternatives:**

- React/Vite SPA — overkill for local personal tool, complicates pipx install
- mpv backend remote control — audio not in browser, contradicts Web UI choice

### Entry Points

```
jjmp3          → Existing interactive CLI (unchanged behavior)
jjmp3 web      → Start FastAPI @ localhost:8765, auto-open browser
```

### Module Structure

```
src/mp3dl/
├── cli.py              # Add `web` subcommand
├── search.py           # Reuse as-is
├── download.py         # Reuse for POST /api/download
├── config.py           # Extend: web_port, cache_dir
├── ui.py               # Unchanged (CLI only)
├── web/
│   ├── __init__.py
│   ├── app.py          # FastAPI app, lifespan, static mount
│   ├── stream.py       # yt-dlp fetch + cache + Range serve
│   ├── models.py       # SQLite schema + CRUD
│   ├── api/
│   │   ├── search.py
│   │   ├── tracks.py
│   │   ├── playlists.py
│   │   ├── queue.py
│   │   ├── history.py
│   │   ├── stream.py
│   │   └── download.py
│   └── static/
│       ├── index.html
│       ├── css/app.css
│       └── js/
│           ├── app.js
│           ├── player.js
│           ├── playlists.js
│           └── api.js
```

### Data Storage

| Data | Location |
|------|----------|
| Config | `~/.config/jjmp3/config.json` |
| Playlists, queue, history | `~/.config/jjmp3/jjmp3.db` (SQLite) |
| Audio cache | `~/.cache/jjmp3/{video_id}.mp3` |

**Config extensions:**

```json
{
  "download_dir": "~/Music/mp3Downloader",
  "web_port": 8765,
  "cache_dir": "~/.cache/jjmp3",
  "cache_max_age_days": 7
}
```

### New Dependencies

- `fastapi`
- `uvicorn[standard]`

Use stdlib `sqlite3` for v1 (no aiosqlite).

---

## 4. Streaming Strategy

### Problem

HTML5 `<audio>` requires HTTP Range requests for seek. Direct yt-dlp pipe (`-o -`) does not support seek reliably.

### Solution: Hybrid Cache + Range Serve

1. User clicks **Play** → backend starts yt-dlp fetch to cache dir
2. Frontend polls `GET /api/stream/{track_id}/status` until `ready: true`
3. Backend serves cached file with `Accept-Ranges: bytes` → seek works
4. Previously played tracks = instant play from cache
5. Cache auto-expire after `cache_max_age_days` (default 7); manual clear via `DELETE /api/cache`

### Stream Endpoints

```
GET  /api/stream/{track_id}         → audio/mpeg, Range support
GET  /api/stream/{track_id}/status  → { ready: bool, progress: 0-100, cached: bool }
DELETE /api/cache                   → clear all cached audio
```

### Download (separate)

```
POST /api/download/{track_id}  → saves MP3 to download_dir (reuse download.py logic)
```

---

## 5. Data Model (SQLite)

```sql
CREATE TABLE playlists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE tracks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    channel     TEXT,
    duration    INTEGER,
    url         TEXT NOT NULL,
    thumbnail   TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE playlist_tracks (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    track_id    INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    PRIMARY KEY (playlist_id, track_id)
);

CREATE TABLE queue (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id    INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    added_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id    INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    played_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Playlist Features

- CRUD unlimited playlists
- Add tracks from: search results, pasted URL, YouTube playlist import
- Drag-and-drop reorder (`position` column)
- **Play playlist** → populates queue without clearing manual queue additions
- **Add to playlist** from search results or track context menu

### YouTube Playlist Import

```
POST /api/import/youtube-playlist
Body: { "url": "https://youtube.com/playlist?list=...", "playlist_id": 1 }
→ yt-dlp --flat-playlist -J → bulk insert tracks + playlist_tracks
```

---

## 6. API Surface

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/search?q=` | YouTube search (reuse search.py) |
| POST | `/api/tracks` | Add track from URL `{ url }` |
| POST | `/api/import/youtube-playlist` | Import YT playlist |
| GET | `/api/playlists` | List playlists |
| POST | `/api/playlists` | Create `{ name }` |
| PUT | `/api/playlists/{id}` | Rename |
| DELETE | `/api/playlists/{id}` | Delete |
| GET | `/api/playlists/{id}/tracks` | List tracks (ordered) |
| POST | `/api/playlists/{id}/tracks` | Add track `{ track_id }` |
| DELETE | `/api/playlists/{id}/tracks/{track_id}` | Remove |
| PUT | `/api/playlists/{id}/tracks/reorder` | `{ track_ids: [3,1,2] }` |
| GET | `/api/queue` | Current queue |
| POST | `/api/queue` | Add `{ track_id }` or `{ playlist_id }` |
| DELETE | `/api/queue/{id}` | Remove item |
| PUT | `/api/queue/reorder` | Reorder |
| DELETE | `/api/queue` | Clear queue |
| GET | `/api/history` | Play history (paginated) |
| GET | `/api/stream/{track_id}` | Stream audio |
| GET | `/api/stream/{track_id}/status` | Cache/buffer status |
| POST | `/api/download/{track_id}` | Download MP3 to folder |
| DELETE | `/api/cache` | Clear audio cache |

Static files served at `/` from `web/static/`.

---

## 7. UI Design

### Reference

Layout and hierarchy inspired by music.youtube.com, white/light theme instead of dark.

### Layout (3 zones)

```
┌──────────────────────────────────────────────────────────────┐
│  [≡]  JJMP3          🔍 Search...                    [⚙]    │
├────────────┬─────────────────────────────────────────────────┤
│  Library   │  Main: Search / Playlist / Queue / History     │
│  Playlists │  Track list with drag handles                  │
│  Queue     │                                                 │
│  History   │                                                 │
│  + New     │                                                 │
├────────────┴─────────────────────────────────────────────────┤
│ [thumb] Title - Artist    ⏮ ▶ ⏭   🔀 🔁   ───●─── 🔊 ──●──  │
└──────────────────────────────────────────────────────────────┘
```

### Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#FFFFFF` | Main background |
| `--bg-sidebar` | `#F8F9FA` | Sidebar |
| `--border` | `#E8EAED` | Dividers |
| `--text-primary` | `#202124` | Headings, titles |
| `--text-secondary` | `#5F6368` | Artist, duration |
| `--hover` | `#F1F3F4` | Row hover |
| `--playing-bg` | `#E0F7FA` | Currently playing row |
| `--accent-cyan` | `#22D3EE` | Play button, links, progress |
| `--accent-magenta` | `#E879F9` | Active nav, logo, left bar |
| `--accent-pink` | `#F472B6` | Secondary highlights |
| `--player-shadow` | `0 -1px 4px rgba(0,0,0,0.08)` | Bottom player bar |

### Components

- **Sidebar** — library nav, playlist list, Queue, History, "+ New playlist"
- **Top bar** — logo, search input, settings (download folder, cache clear)
- **Track list** — `#` / thumbnail / title / artist / duration / `⋮` menu
- **Playing row** — magenta left bar + `--playing-bg`
- **Drag handle** on each row for reorder
- **Bottom player** — thumbnail, title/artist, controls, seek bar, volume
- **Context menu (`⋮`)** — Play, Play next, Add to playlist, Download, Remove

### Interactions

- Click row → play
- Drag row → reorder (playlist or queue)
- Track ends → auto `playNext()` + log to history
- Repeat cycles: `off` → `one` → `all`
- Shuffle: random without repeat until all played

### Responsive (v1)

- Desktop-first (≥1024px)
- Tablet: sidebar collapses to icons
- Mobile: out of scope v1

---

## 8. Playback Logic (Frontend)

### Queue vs Playlist

| | Playlist | Queue |
|--|----------|-------|
| Persistent | Yes (DB) | Yes (DB, survives refresh) |
| Reorder | Drag-drop | Drag-drop |
| Source | Manual curation | "Play playlist" or "Play now" |

### Client State

```javascript
{
  currentTrack: Track | null,
  queue: Track[],
  queueIndex: number,
  shuffle: boolean,
  repeat: 'off' | 'one' | 'all',
  volume: 0.0 - 1.0,
  isPlaying: boolean
}
```

---

## 9. Error Handling

| Scenario | Behavior |
|----------|----------|
| yt-dlp/ffmpeg missing | Banner on web UI startup check; block stream/download |
| Track unavailable | Toast error, skip to next in queue |
| Cache write fail | Show error, suggest clear cache |
| Port in use | CLI message: port in use, set `web_port` in config |
| Invalid YouTube URL | 400 with clear message |

---

## 10. Security (Local-Only)

- Bind server to `127.0.0.1` only (not `0.0.0.0`)
- No auth required (single user local tool)
- Same-origin static + API (no CORS needed)

---

## 11. Testing Plan

- Unit: SQLite CRUD, track dedup by video_id
- Integration: search API, add track from URL, playlist CRUD
- Manual: stream + seek, shuffle/repeat, drag-drop reorder, import YT playlist, download, CLI unchanged

---

## 12. Implementation Phases

1. **Foundation** — FastAPI skeleton, `jjmp3 web`, SQLite, search API
2. **Streaming** — cache + stream endpoints, basic player bar
3. **Playlists** — CRUD, reorder, import YouTube playlist
4. **Queue & History** — queue management, shuffle/repeat, history log
5. **UI Polish** — YT Music-like layout, white theme, JJMP3 accents
6. **Download** — download button in web UI

---

## 13. Open Items

None — all decisions resolved in brainstorming.
