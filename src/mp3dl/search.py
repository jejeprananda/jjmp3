"""YouTube search via yt-dlp ytsearch."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    title: str
    channel: str
    duration: int | None
    video_id: str
    url: str


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "?"
    seconds = int(seconds)
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_result_line(index: int, result: SearchResult) -> str:
    duration = format_duration(result.duration)
    channel = result.channel or "?"
    return f"{index}. {result.title} | {channel} | {duration}"


def search_youtube(query: str, limit: int = 10) -> list[SearchResult]:
    """Search YouTube with yt-dlp and return up to `limit` results."""
    search_term = f"ytsearch{limit}:{query}"
    proc = subprocess.run(
        ["yt-dlp", "--flat-playlist", "-J", search_term],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "yt-dlp search failed").strip()
        raise RuntimeError(err)

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Failed to parse yt-dlp search output as JSON") from exc

    entries = payload.get("entries") or []
    results: list[SearchResult] = []
    for entry in entries:
        if not entry:
            continue
        video_id = entry.get("id") or ""
        if not video_id:
            continue
        url = entry.get("url") or entry.get("webpage_url")
        if not url:
            url = f"https://www.youtube.com/watch?v={video_id}"
        results.append(
            SearchResult(
                title=entry.get("title") or "(untitled)",
                channel=entry.get("uploader")
                or entry.get("channel")
                or entry.get("uploader_id")
                or "",
                duration=entry.get("duration"),
                video_id=video_id,
                url=url,
            )
        )
    return results
