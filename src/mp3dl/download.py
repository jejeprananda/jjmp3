"""Download and extract audio to MP3 via yt-dlp."""

from __future__ import annotations

import subprocess
from pathlib import Path

OUTPUT_DIR = Path.home() / "Music" / "mp3Downloader"
OUTPUT_TEMPLATE = str(OUTPUT_DIR / "%(title)s.%(ext)s")


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


def download_mp3(url: str) -> None:
    """Extract best audio from `url` as MP3 into OUTPUT_DIR."""
    ensure_output_dir()
    proc = subprocess.run(
        [
            "yt-dlp",
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",
            "-o",
            OUTPUT_TEMPLATE,
            url,
        ],
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Download failed (exit code {proc.returncode})")
