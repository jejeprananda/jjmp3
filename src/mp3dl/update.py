"""Self-update JJMP3 from GitHub via pipx."""

from __future__ import annotations

import re
import shutil
import subprocess
import urllib.error
import urllib.request
from importlib.metadata import PackageNotFoundError, version

from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mp3dl import __version__ as fallback_version
from mp3dl.ui import console, error_panel, info_panel, success_panel

REPO_GIT = "https://github.com/jejeprananda/jjmp3.git"
REMOTE_PYPROJECT = (
    "https://raw.githubusercontent.com/jejeprananda/jjmp3/main/pyproject.toml"
)
_VERSION_RE = re.compile(r'^version\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def get_local_version() -> str:
    try:
        return version("jjmp3")
    except PackageNotFoundError:
        return fallback_version


def get_remote_version(timeout: float = 15.0) -> str:
    req = urllib.request.Request(
        REMOTE_PYPROJECT,
        headers={"User-Agent": "jjmp3-updater"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gagal cek versi remote: {exc}") from exc

    match = _VERSION_RE.search(text)
    if not match:
        raise RuntimeError("Tidak menemukan version di pyproject.toml remote")
    return match.group(1)


def _parse_version(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in value.strip().split("."):
        digits = re.match(r"(\d+)", chunk)
        parts.append(int(digits.group(1)) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer(remote: str, local: str) -> bool:
    return _parse_version(remote) > _parse_version(local)


def _checklist(steps: list[tuple[str, str]]) -> Panel:
    """steps: list of (status, label) where status in pending|active|done|fail."""
    table = Table.grid(padding=(0, 1))
    icons = {
        "pending": Text("○", style="dim"),
        "active": Text("●", style="cyan bold"),
        "done": Text("✓", style="green bold"),
        "fail": Text("✗", style="red bold"),
    }
    for status, label in steps:
        style = {
            "pending": "dim",
            "active": "cyan",
            "done": "green",
            "fail": "red",
        }.get(status, "")
        table.add_row(icons.get(status, Text("?")), Text(label, style=style))
    return Panel(table, title="[bold]Update[/]", border_style="magenta", padding=(0, 1))


def run_update() -> bool:
    """Check GitHub for a newer version and install via pipx. Returns True if updated."""
    local = get_local_version()
    info_panel(f"Versi terpasang: [cyan]{local}[/]", title="Update", style="magenta")

    steps = [
        ("active", "Cek versi terbaru di GitHub"),
        ("pending", "Bandingkan dengan versi lokal"),
        ("pending", "Install update via pipx"),
        ("pending", "Selesai"),
    ]

    with Live(_checklist(steps), console=console, refresh_per_second=8) as live:
        try:
            remote = get_remote_version()
        except RuntimeError as exc:
            steps[0] = ("fail", f"Cek versi gagal: {exc}")
            live.update(_checklist(steps))
            error_panel(str(exc), title="Update gagal")
            return False

        steps[0] = ("done", f"Versi remote: {remote}")
        steps[1] = ("active", "Bandingkan dengan versi lokal")
        live.update(_checklist(steps))

        if not is_newer(remote, local):
            steps[1] = ("done", f"Sudah terbaru ({local})")
            steps[2] = ("done", "Install dilewati")
            steps[3] = ("done", "Selesai")
            live.update(_checklist(steps))
            success_panel(
                f"JJMP3 sudah di versi terbaru: [bold]{local}[/]",
                title="Up to date",
            )
            return False

        steps[1] = ("done", f"Update tersedia: {local} → {remote}")
        steps[2] = ("active", "Install update via pipx…")
        live.update(_checklist(steps))

        if shutil.which("pipx") is None:
            steps[2] = ("fail", "pipx tidak ditemukan")
            live.update(_checklist(steps))
            error_panel(
                "pipx tidak ada di PATH.\n"
                f"Update manual: [cyan]pipx install --force git+{REPO_GIT}[/]",
                title="Update gagal",
            )
            return False

        proc = subprocess.run(
            ["pipx", "install", "--force", f"git+{REPO_GIT}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "pipx gagal").strip()
            steps[2] = ("fail", "Install update gagal")
            live.update(_checklist(steps))
            error_panel(err, title="Update gagal")
            return False

        steps[2] = ("done", f"Terpasang {remote}")
        steps[3] = ("done", "Selesai — jalankan ulang jjmp3")
        live.update(_checklist(steps))

    success_panel(
        f"Berhasil update [bold]{local}[/] → [bold]{remote}[/]\n"
        "Jalankan ulang [cyan]jjmp3[/] agar proses ini memakai kode baru.",
        title="Updated",
    )
    return True
