"""Download and extract audio to MP3 via yt-dlp."""

from __future__ import annotations

import subprocess
from pathlib import Path

from mp3dl.config import get_download_dir


def ensure_output_dir(output_dir: Path | None = None) -> Path:
    path = output_dir or get_download_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def download_mp3(url: str, output_dir: Path | None = None) -> Path:
    """Extract best audio from `url` as MP3 into the configured download dir."""
    path = ensure_output_dir(output_dir)
    output_template = str(path / "%(title)s.%(ext)s")
    proc = subprocess.run(
        [
            "yt-dlp",
            "-x",
            "--audio-format",
            "mp3",
            "--audio-quality",
            "0",
            "-o",
            output_template,
            url,
        ],
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Download failed (exit code {proc.returncode})")
    return path
