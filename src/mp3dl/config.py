"""Persistent JJMP3 settings (~/.config/jjmp3/config.json)."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_DOWNLOAD_DIR = Path.home() / "Music" / "mp3Downloader"
CONFIG_DIR = Path.home() / ".config" / "jjmp3"
CONFIG_PATH = CONFIG_DIR / "config.json"


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
