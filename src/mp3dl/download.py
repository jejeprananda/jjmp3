"""Download and extract audio to MP3 via yt-dlp."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

from mp3dl.config import get_download_dir
from mp3dl.ui import console
from mp3dl.ytdlp import ytdlp_cmd

_PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)%")
_DEST_RE = re.compile(r"Destination:\s*(.+)$")
ProgressCallback = Callable[[float], None]


def ensure_output_dir(output_dir: Path | None = None) -> Path:
    path = output_dir or get_download_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _step_icon(status: str) -> Text:
    return {
        "pending": Text("○", style="dim"),
        "active": Text("●", style="cyan bold"),
        "done": Text("✓", style="green bold"),
        "fail": Text("✗", style="red bold"),
    }.get(status, Text("?"))


def _render_download_ui(
    steps: list[tuple[str, str]],
    progress: Progress,
) -> Panel:
    table = Table.grid(padding=(0, 1))
    for status, label in steps:
        style = {
            "pending": "dim",
            "active": "cyan",
            "done": "green",
            "fail": "red",
        }.get(status, "")
        table.add_row(_step_icon(status), Text(label, style=style))
    table.add_row(Text(""), Text(""))
    table.add_row(Text(""), progress)
    return Panel(
        table,
        title="[bold]Download[/]",
        border_style="bright_blue",
        padding=(0, 1),
    )


def download_mp3(url: str, output_dir: Path | None = None) -> Path:
    """Extract best audio from `url` as MP3 with checklist + progress bar."""
    path = ensure_output_dir(output_dir)
    output_template = str(path / "%(title)s.%(ext)s")

    steps: list[tuple[str, str]] = [
        ("done", f"Folder siap: {path}"),
        ("active", "Mengunduh dari YouTube"),
        ("pending", "Konversi ke MP3"),
        ("pending", "Selesai"),
    ]

    progress = Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=28),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
        expand=True,
    )
    task_id = progress.add_task("Menunggu…", total=100)

    saved_path: str | None = None
    extracting = False

    cmd = ytdlp_cmd(
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--newline",
        "--progress",
        "-o",
        output_template,
        url,
    )

    with Live(
        _render_download_ui(steps, progress),
        console=console,
        refresh_per_second=12,
    ) as live:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        try:
            for raw in proc.stdout:
                line = raw.strip()
                if not line:
                    live.update(_render_download_ui(steps, progress))
                    continue

                lower = line.lower()
                if "[download]" in lower:
                    if not extracting:
                        steps[1] = ("active", "Mengunduh dari YouTube")
                    match = _PERCENT_RE.search(line)
                    if match:
                        pct = min(float(match.group(1)), 100.0)
                        progress.update(
                            task_id,
                            completed=pct,
                            description="Download",
                        )
                    dest = _DEST_RE.search(line)
                    if dest and not line.lower().endswith(".mp3"):
                        # intermediate media file
                        pass

                if "[extractaudio]" in lower or "extractaudio" in lower.replace(" ", ""):
                    extracting = True
                    steps[1] = ("done", "Unduhan selesai")
                    steps[2] = ("active", "Konversi ke MP3")
                    progress.update(task_id, completed=100, description="Konversi")
                    dest = _DEST_RE.search(line)
                    if dest:
                        saved_path = dest.group(1).strip()

                if "deleting original file" in lower:
                    steps[2] = ("active", "Membersihkan file sementara")

                if "error" in lower and "warning" not in lower:
                    # keep streaming; final returncode decides failure
                    pass

                live.update(_render_download_ui(steps, progress))
        finally:
            proc.wait()

        if proc.returncode != 0:
            steps[1] = ("fail", "Unduhan gagal") if not extracting else steps[1]
            if extracting:
                steps[2] = ("fail", "Konversi gagal")
            live.update(_render_download_ui(steps, progress))
            raise RuntimeError(f"Download failed (exit code {proc.returncode})")

        steps[1] = ("done", "Unduhan selesai")
        steps[2] = ("done", "Konversi ke MP3")
        if saved_path:
            steps[3] = ("done", f"Tersimpan: {Path(saved_path).name}")
        else:
            steps[3] = ("done", f"Tersimpan di {path}")
        progress.update(task_id, completed=100, description="Selesai")
        live.update(_render_download_ui(steps, progress))

    if saved_path:
        return Path(saved_path)
    # Fallback: newest mp3 in folder
    mp3s = sorted(path.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
    return mp3s[0] if mp3s else path


def download_mp3_quiet(
    url: str,
    output_dir: Path | None = None,
    *,
    output_template: str | None = None,
    on_progress: ProgressCallback | None = None,
) -> Path:
    """Download MP3 without Rich UI. Returns the saved file path."""
    path = ensure_output_dir(output_dir)
    template = output_template or str(path / "%(title)s.%(ext)s")
    cmd = ytdlp_cmd(
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--newline",
        "--progress",
        "-o",
        template,
        url,
    )
    saved_path: str | None = None
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    tail: list[str] = []
    for raw in proc.stdout:
        line = raw.strip()
        if not line:
            continue
        tail.append(line)
        if len(tail) > 30:
            tail.pop(0)
        match = _PERCENT_RE.search(line)
        if match and on_progress:
            on_progress(min(float(match.group(1)), 99.0))
        dest = _DEST_RE.search(line)
        if dest and line.lower().endswith(".mp3"):
            saved_path = dest.group(1).strip()
        if "[ExtractAudio]" in line or "Destination:" in line:
            dest = _DEST_RE.search(line)
            if dest:
                candidate = dest.group(1).strip()
                if candidate.lower().endswith(".mp3"):
                    saved_path = candidate
    proc.wait()
    if proc.returncode != 0:
        err = "\n".join(tail).strip() or f"yt-dlp exit {proc.returncode}"
        if "ERROR:" in err:
            err = err[err.rfind("ERROR:") :].strip()
        raise RuntimeError(err[:500])

    if saved_path and Path(saved_path).is_file():
        return Path(saved_path)

    # Resolve from template stem
    stem_path = Path(template.replace("%(ext)s", "mp3").replace(".%(ext)s", ".mp3"))
    if "%(" not in str(stem_path) and stem_path.is_file():
        return stem_path

    mp3s = sorted(path.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
    if mp3s:
        return mp3s[0]
    raise RuntimeError("Download finished but MP3 file not found")
