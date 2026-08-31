"""Persistent JJMP3 settings (~/.config/jjmp3/config.json)."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_DOWNLOAD_DIR = Path.home() / "Music" / "mp3Downloader"
DEFAULT_WEB_PORT = 8765
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "jjmp3"
DEFAULT_CACHE_MAX_AGE_DAYS = 7
CONFIG_DIR = Path.home() / ".config" / "jjmp3"
CONFIG_PATH = CONFIG_DIR / "config.json"
DB_PATH = CONFIG_DIR / "jjmp3.db"


def config_exists() -> bool:
    return CONFIG_PATH.is_file()


def load_config() -> dict:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def get_download_dir() -> Path:
    raw = load_config().get("download_dir")
    if isinstance(raw, str) and raw.strip():
        return Path(raw).expanduser().resolve()
    return DEFAULT_DOWNLOAD_DIR.resolve()


def set_download_dir(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    data = load_config()
    data["download_dir"] = str(resolved)
    save_config(data)
    return resolved


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
