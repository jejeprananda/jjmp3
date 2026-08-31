"""Resolve yt-dlp executable and shared CLI flags."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def ytdlp_path() -> str:
    """Prefer yt-dlp from the same venv as jjmp3 (pip/pipx install)."""
    # Do not resolve sys.executable — venv python is often a symlink to /usr/bin.
    venv_bin = Path(sys.executable).parent
    bundled = venv_bin / "yt-dlp"
    if bundled.is_file():
        return str(bundled.resolve())
    local = Path.home() / ".local" / "bin" / "yt-dlp"
    if local.is_file():
        return str(local)
    found = shutil.which("yt-dlp")
    if found:
        return found
    raise FileNotFoundError("yt-dlp not found")


def ytdlp_cmd(*args: str) -> list[str]:
    cmd = [ytdlp_path(), "--no-update"]
    node = shutil.which("node")
    if node:
        cmd.extend(["--js-runtimes", f"node:{node}"])
    cmd.extend(args)
    return cmd
