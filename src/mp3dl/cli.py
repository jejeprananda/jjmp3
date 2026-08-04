"""Interactive CLI entry point."""

from __future__ import annotations

import shutil

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.utils import get_style

from mp3dl.config import (
    DEFAULT_DOWNLOAD_DIR,
    config_exists,
    get_download_dir,
    set_download_dir,
)
from mp3dl.download import download_mp3
from mp3dl.search import SearchResult, format_duration, search_youtube
from mp3dl.ui import (
    console,
    error_panel,
    info_panel,
    show_banner,
    success_panel,
)

PROMPT_STYLE = get_style(
    {
        "questionmark": "#e879f9 bold",
        "answermark": "#22d3ee",
        "answer": "#22d3ee bold",
        "input": "#f8fafc",
        "question": "#f8fafc bold",
        "pointer": "#22d3ee bold",
        "highlighted": "#22d3ee bold",
        "fuzzy_prompt": "#a78bfa",
        "fuzzy_info": "#64748b",
        "fuzzy_match": "#f472b6 bold",
        "instruction": "#64748b",
    },
    style_override=False,
)


def check_dependencies() -> list[str]:
    missing: list[str] = []
    if shutil.which("yt-dlp") is None:
        missing.append("yt-dlp")
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
    return missing


def _prompt_download_dir(current: str | None = None) -> str | None:
    default = current or str(DEFAULT_DOWNLOAD_DIR)
    try:
        value = inquirer.text(
            message="Download directory:",
            default=default,
            style=PROMPT_STYLE,
            amark="✓",
            qmark="⚙",
            instruction="(Enter untuk pakai path ini · ~ didukung)",
        ).execute()
    except KeyboardInterrupt:
        console.print()
        return None
    if value is None:
        return None
    return str(value).strip() or default


def run_settings(*, first_run: bool = False) -> bool:
    """Ask and save download directory. Returns False if cancelled."""
    if first_run:
        info_panel(
            "Setup awal: pilih folder penyimpanan MP3.\n"
            "Nanti bisa diubah kapan saja dengan mengetik [bold]/setting[/] di prompt pencarian.",
            title="Welcome",
            style="bright_blue",
        )
    else:
        info_panel(
            f"Folder saat ini: [cyan]{get_download_dir()}[/]\n"
            f"Config: [dim]~/.config/jjmp3/config.json[/]",
            title="Settings",
            style="magenta",
        )

    chosen = _prompt_download_dir(str(get_download_dir()) if config_exists() else None)
    if chosen is None:
        return False
    try:
        path = set_download_dir(chosen)
    except OSError as exc:
        error_panel(str(exc), title="Gagal simpan setting")
        return False
    success_panel(f"Download directory: [cyan]{path}[/]", title="Tersimpan")
    return True


def _prompt_query() -> str | None:
    try:
        return inquirer.text(
            message="Cari lagu / artis:",
            instruction="(Enter kosong = keluar · /setting = ubah folder · typo ringan OK)",
            style=PROMPT_STYLE,
            amark="✓",
            qmark="♪",
        ).execute()
    except KeyboardInterrupt:
        console.print()
        return None


def _choice_label(result: SearchResult) -> str:
    duration = format_duration(result.duration)
    channel = result.channel or "?"
    return f"{result.title}  ·  {channel}  ·  {duration}"


def _prompt_choice(results: list[SearchResult]) -> SearchResult | None:
    # Use indexes as values — InquirerPy fuzzy may coerce dataclasses to dict.
    choices = [
        Choice(value=i, name=_choice_label(result))
        for i, result in enumerate(results)
    ]
    choices.append(Choice(value=None, name="← Batal / cari ulang"))
    try:
        selected = inquirer.fuzzy(
            message="Pilih hasil (↑↓ · ketik untuk filter):",
            choices=choices,
            style=PROMPT_STYLE,
            amark="✓",
            qmark="▶",
            instruction="arrow + Enter · ketik untuk filter · Esc batal",
            border=True,
            max_height="60%",
        ).execute()
    except KeyboardInterrupt:
        console.print()
        return None

    if selected is None:
        return None
    if isinstance(selected, int) and 0 <= selected < len(results):
        return results[selected]
    return None


def _prompt_again() -> bool:
    try:
        return inquirer.confirm(
            message="Cari lagi?",
            default=True,
            style=PROMPT_STYLE,
            amark="✓",
            qmark="?",
        ).execute()
    except KeyboardInterrupt:
        console.print()
        return False


def main() -> int:
    missing = check_dependencies()
    if missing:
        names = ", ".join(missing)
        error_panel(
            f"Dependensi tidak ditemukan: [bold]{names}[/]\n\n"
            "Pasang yt-dlp dan ffmpeg, lalu pastikan keduanya ada di PATH.\n"
            "Contoh: [cyan]pip install -U yt-dlp[/]  |  [cyan]sudo apt install ffmpeg[/]",
            title="Dependensi",
        )
        return 1

    if not config_exists():
        if not run_settings(first_run=True):
            console.print("[dim]Setup dibatalkan. Jalankan jjmp3 lagi untuk setup.[/]")
            return 1

    download_dir = get_download_dir()
    show_banner(str(download_dir))
    info_panel(
        "Ketik query pencarian, atau [bold]/setting[/] untuk ubah folder download.\n"
        "Pilih lagu dengan panah ↑↓, atau ketik untuk memfilter daftar.",
        title="Cara pakai",
        style="bright_blue",
    )

    while True:
        query = _prompt_query()
        if query is None:
            return 0
        query = query.strip()
        if not query:
            console.print("[dim]Sampai jumpa.[/]")
            return 0

        if query.lower() in {"/setting", "/settings", "/config"}:
            run_settings(first_run=False)
            continue

        with console.status("[cyan]Mencari di YouTube…[/]", spinner="dots"):
            try:
                results = search_youtube(query)
            except RuntimeError as exc:
                error_panel(str(exc), title="Pencarian gagal")
                if not _prompt_again():
                    return 0
                continue

        if not results:
            info_panel("Tidak ada hasil untuk query itu. Coba kata kunci lain.", title="Kosong")
            if not _prompt_again():
                return 0
            continue

        selected = _prompt_choice(results)
        if selected is None:
            if not _prompt_again():
                return 0
            continue

        out_dir = get_download_dir()
        info_panel(f"[bold]{selected.title}[/]\n{selected.url}", title="Mengunduh")
        try:
            download_mp3(selected.url, out_dir)
        except RuntimeError as exc:
            error_panel(str(exc), title="Download gagal")
        else:
            success_panel(
                f"[bold]{selected.title}[/]\nDisimpan di [cyan]{out_dir}[/]",
                title="Selesai",
            )

        if not _prompt_again():
            console.print("[dim]Sampai jumpa.[/]")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
