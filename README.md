# JJMP3

**Current version: `0.4.1`**

JJMP3 is an **open-source** app to search YouTube, download audio as MP3, and play it from a local folder — via a **CLI** or a **Web UI** styled like a music player. It is made to be music listener that cant or wont afford an adfree music platform.

**Repo:** https://github.com/jejeprananda/jjmp3  
**License:** [MIT](LICENSE)

---

## What is it for?

| Mode | Purpose |
|------|---------|
| **CLI** (`jjmp3`) | Search YouTube → pick a result → download MP3 to your folder |
| **Web UI** (`jjmp3-web`) | Local library, search & download, file explorer, JSON playlists, player with shuffle/repeat |
| **Desktop launcher** | Shows up in OS app search (Linux / macOS / Windows) |

The Web UI does **not** stream YouTube live. The player only plays MP3 files already in your download folder. Search is for **downloading**; if a track already exists (same `video_id` or matching title), you get an *Already downloaded* badge and a new download is blocked.

Close the browser tab = the Web UI server stops automatically.

---

## Languages & stack

| Layer | Tech |
|-------|------|
| Main language | **Python ≥ 3.10** |
| CLI | Rich, InquirerPy |
| Web server | FastAPI + Uvicorn |
| Frontend | HTML / CSS / Vanilla JS (ES modules), GSAP (vendored) |
| Audio download | **yt-dlp** + **ffmpeg** |
| Data | JSON in the download folder (`library.json`, `playlists.json`) + config in `~/.config/jjmp3/` |

No React/Vite — the frontend ships with the Python package so `pipx install` stays simple.

---

## Prerequisites

- Python 3.10+
- [`pipx`](https://pipx.pypa.io/) (recommended for a global install)
- `ffmpeg` on PATH
- `yt-dlp` (usually installed as a Python dependency; keep it on PATH if you use a standalone binary)

```bash
# Ubuntu / Debian
sudo apt install ffmpeg pipx
pipx ensurepath
# open a new terminal after ensurepath
```

---

## Install

### Quick install (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/jejeprananda/jjmp3/main/install.sh | bash
```

The installer will:

1. Ask for a download folder (default `~/Music/mp3Downloader`)
2. Save config to `~/.config/jjmp3/config.json`
3. Install `jjmp3` via pipx
4. Register an OS launcher (`jjmp3-desktop install`)

### pipx directly

```bash
pipx install git+https://github.com/jejeprananda/jjmp3.git
jjmp3-desktop install   # optional: add to the app menu
```

### From a clone (development)

```bash
git clone https://github.com/jejeprananda/jjmp3.git
cd jjmp3
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
jjmp3-desktop install
```

Or: `bash install.sh` / `pipx install .`

### Commands after install

| Command | Purpose |
|---------|---------|
| `jjmp3` | Interactive CLI (download) |
| `jjmp3 web` | Same as `jjmp3-web` |
| `jjmp3-web` | Start Web UI and open the browser |
| `jjmp3-desktop install` | Install the OS launcher |
| `jjmp3-desktop uninstall` | Remove the launcher |

Search for **"JJMP3"** in the Linux app menu, macOS Spotlight/Launchpad, or Windows Start Menu.

---

## Usage

### CLI

```bash
jjmp3
```

1. Type a search query (or `/setting` / `/update`)
2. Pick a result with ↑↓ (type to filter)
3. The MP3 is saved to your download folder (checklist + progress)

Special prompts:

| Input | Action |
|-------|--------|
| `/setting` | Change download folder |
| `/update` | Check & install update from GitHub via pipx |
| Empty Enter | Quit |

### Web UI

```bash
jjmp3-web
# or
jjmp3 web
```

Opens `http://127.0.0.1:8765` (localhost only).

| View | Purpose |
|------|---------|
| **Library** | List and play all MP3s in the download folder |
| **Search** | Search YouTube → click to download. Already present → play local file |
| **Explorer** | Browse the same folder (delete files, add to playlists) |
| **Playlists** | Create / rename / delete playlists; visual + JSON editor |
| **Settings** | Download folder, check for updates, see version |

Player controls: play/pause, prev/next, shuffle, repeat (off/one/all), seek, volume. Shortcuts: `Space`, `←` / `→` (when not typing).

**Lifecycle:** the browser tab sends heartbeats; closing the last tab stops the server process.

---

## Settings & configuration

### Config file

`~/.config/jjmp3/config.json`

```json
{
  "download_dir": "/home/you/Music/mp3Downloader",
  "web_port": 8765,
  "cache_dir": "/home/you/.cache/jjmp3",
  "cache_max_age_days": 7
}
```

| Key | Default | Notes |
|-----|---------|-------|
| `download_dir` | `~/Music/mp3Downloader` | Single folder for library / explorer / playlists |
| `web_port` | `8765` | Web UI port (localhost) |
| `cache_dir` | `~/.cache/jjmp3` | Legacy; stream cache is no longer used by the Web UI |
| `cache_max_age_days` | `7` | Legacy |

Change `download_dir` via:

- Web UI → **Settings** → Apply
- CLI → `/setting`

### Download folder layout

```
{download_dir}/
  Song.mp3
  covers/{video_id}.jpg     # thumbnail (optional)
  library.json              # video_id ↔ file index (automatic)
  playlists.json            # user playlists
```

Example `playlists.json`:

```json
{
  "version": 1,
  "playlists": [
    {
      "id": "pl_workout",
      "name": "Workout",
      "tracks": ["Song A.mp3", "Song B.mp3"]
    }
  ]
}
```

Tracks are referenced by **relative filenames**, not YouTube IDs. The Web UI editor supports visual edits or raw JSON.

---

## Update & uninstall

### Update

- Web UI → **Settings** → **Check for updates** → **Install update**
- CLI: `/update`
- Manual:

```bash
pipx install --force git+https://github.com/jejeprananda/jjmp3.git
jjmp3-desktop install
```

After updating, **restart** the Web UI so the process loads the new code.

### Uninstall

```bash
jjmp3-desktop uninstall
pipx uninstall jjmp3
# optional:
# rm -rf ~/.config/jjmp3
```

---

## Development & contributing

JJMP3 is **open source** — contributions are welcome.

### Local setup

```bash
git clone https://github.com/jejeprananda/jjmp3.git
cd jjmp3
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

### Layout (short)

```
src/mp3dl/
  cli.py              # CLI entry
  download.py         # yt-dlp → MP3
  search.py           # ytsearch
  update.py           # check/install updates from GitHub
  desktop.py          # OS launcher
  config.py           # ~/.config/jjmp3
  web/
    app.py            # FastAPI
    launcher.py       # jjmp3-web + lifecycle shutdown
    library.py        # folder scan, index, Range serve
    playlists_store.py
    jobs.py           # background downloads
    static/           # Web UI
tests/
```

### Contribution ideas

- Bug fixes & regression tests
- Web UI UX / accessibility
- Better ID3 metadata / cover art
- Packaging (AppImage, Flatpak, etc.)
- Docs & translations

Flow: fork → branch → PR to `main`. Explain *why* the change helps. Keep CLI and Web UI installable via pipx without a separate frontend build.

### Tests

```bash
pytest -q
```

---

## Legal note

Only download content you are allowed to (copyright / YouTube ToS). JJMP3 is a personal wrapper around [yt-dlp](https://github.com/yt-dlp/yt-dlp).

---

## Changelog (short)

| Version | Notes |
|---------|-------|
| **0.4.1** | Title-based download dedup, smoother progress UI, full README, version in the app |
| **0.4.0** | Local library player, JSON playlists, OS launcher, icon, Settings → Updates |
| **0.3.x** | Web streaming + SQLite playlists (replaced in 0.4) |

---

Made with ☕ · MIT License · [Issues](https://github.com/jejeprananda/jjmp3/issues)
