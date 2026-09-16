"""Visual CLI helpers: logo, panels, styled prompts."""

from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

console = Console()

LOGO = r"""
     ██╗     ██╗███╗   ███╗██████╗ ██████╗
     ██║     ██║████╗ ████║██╔══██╗╚════██╗
     ██║     ██║██╔████╔██║██████╔╝ █████╔╝
██   ██║██   ██║██║╚██╔╝██║██╔═══╝  ╚═══██╗
╚█████╔╝╚█████╔╝██║ ╚═╝ ██║██║     ██████╔╝
 ╚════╝  ╚════╝ ╚═╝     ╚═╝╚═╝     ╚═════╝
"""


def show_banner(output_dir: str) -> None:
    from mp3dl.update import get_local_version

    logo = Text(LOGO, style="bold cyan")
    subtitle = Text(
        f"YouTube → MP3  ·  powered by yt-dlp  ·  v{get_local_version()}",
        style="dim",
    )
    body = Group(Align.center(logo), Align.center(subtitle))
    console.print(
        Panel(
            body,
            title="[bold magenta]JJMP3[/]",
            subtitle=f"[dim]{output_dir}[/]",
            border_style="bright_blue",
            padding=(0, 2),
        )
    )


def info_panel(message: str, title: str = "Info", style: str = "cyan") -> None:
    console.print(
        Panel(
            message,
            title=f"[bold]{title}[/]",
            border_style=style,
            padding=(0, 1),
        )
    )


def error_panel(message: str, title: str = "Error") -> None:
    console.print(
        Panel(
            message,
            title=f"[bold red]{title}[/]",
            border_style="red",
            padding=(0, 1),
        )
    )


def success_panel(message: str, title: str = "Selesai") -> None:
    console.print(
        Panel(
            message,
            title=f"[bold green]{title}[/]",
            border_style="green",
            padding=(0, 1),
        )
    )
