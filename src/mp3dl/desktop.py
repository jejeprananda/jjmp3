"""Install OS launcher entries (Linux, macOS, Windows)."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import textwrap
from importlib.resources import files
from pathlib import Path


def _jjmp3_web_exe() -> str:
    exe = shutil.which("jjmp3-web")
    if exe:
        return exe
    return "jjmp3-web"


def _icon_asset() -> tuple[str, bytes] | None:
    for name in ("jjmp3.png", "jjmp3.svg"):
        try:
            ref = files("mp3dl") / "data" / "icons" / name
            if ref.is_file():
                return name, ref.read_bytes()
        except (FileNotFoundError, ModuleNotFoundError, TypeError, OSError):
            continue
    fallback = Path(__file__).resolve().parent / "data" / "icons"
    for name in ("jjmp3.png", "jjmp3.svg"):
        path = fallback / name
        if path.is_file():
            return name, path.read_bytes()
    return None


def install_linux() -> Path:
    apps = Path.home() / ".local" / "share" / "applications"
    apps.mkdir(parents=True, exist_ok=True)
    dest = apps / "jjmp3-web.desktop"
    exe = _jjmp3_web_exe()
    icon_line = "Icon=multimedia-player"
    icon = _icon_asset()
    if icon:
        name, data = icon
        ext = Path(name).suffix.lower()
        size_dir = "scalable" if ext == ".svg" else "256x256"
        icons_dir = Path.home() / ".local" / "share" / "icons" / "hicolor" / size_dir / "apps"
        icons_dir.mkdir(parents=True, exist_ok=True)
        (icons_dir / f"jjmp3{ext}").write_bytes(data)
        icon_line = "Icon=jjmp3"

    content = textwrap.dedent(
        f"""\
        [Desktop Entry]
        Type=Application
        Name=JJMP3
        GenericName=Music Player
        Comment=Local music player — search, download, and play MP3s
        Exec={exe}
        Terminal=false
        Categories=AudioVideo;Audio;Player;
        Keywords=music;mp3;player;youtube;download;jjmp3;
        StartupNotify=true
        {icon_line}
        """
    )
    dest.write_text(content, encoding="utf-8")
    dest.chmod(0o755)
    _try_update_desktop_database()
    return dest


def _try_update_desktop_database() -> None:
    if shutil.which("update-desktop-database"):
        apps = Path.home() / ".local" / "share" / "applications"
        subprocess.run(
            ["update-desktop-database", str(apps)],
            check=False,
            capture_output=True,
        )


def install_macos() -> Path:
    app = Path.home() / "Applications" / "JJMP3.app"
    contents = app / "Contents"
    macos = contents / "MacOS"
    resources = contents / "Resources"
    macos.mkdir(parents=True, exist_ok=True)
    resources.mkdir(parents=True, exist_ok=True)

    exe = _jjmp3_web_exe()
    launcher = macos / "jjmp3-web"
    launcher.write_text(
        textwrap.dedent(
            f"""\
            #!/bin/bash
            exec "{exe}"
            """
        ),
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    icon = _icon_asset()
    if icon:
        name, data = icon
        (resources / name).write_bytes(data)

    plist = textwrap.dedent(
        """\
        <?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>CFBundleName</key>
            <string>JJMP3</string>
            <key>CFBundleDisplayName</key>
            <string>JJMP3</string>
            <key>CFBundleIdentifier</key>
            <string>dev.jjmp3.web</string>
            <key>CFBundleVersion</key>
            <string>1.0</string>
            <key>CFBundlePackageType</key>
            <string>APPL</string>
            <key>CFBundleExecutable</key>
            <string>jjmp3-web</string>
            <key>LSApplicationCategoryType</key>
            <string>public.app-category.music</string>
            <key>NSHighResolutionCapable</key>
            <true/>
        </dict>
        </plist>
        """
    )
    (contents / "Info.plist").write_text(plist, encoding="utf-8")
    return app


def install_windows() -> Path:
    start_menu = (
        Path(os.environ.get("APPDATA", ""))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
    )
    start_menu.mkdir(parents=True, exist_ok=True)
    shortcut = start_menu / "JJMP3.lnk"
    exe = _jjmp3_web_exe()
    ps = textwrap.dedent(
        f"""
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{shortcut}")
        $Shortcut.TargetPath = "{exe}"
        $Shortcut.WorkingDirectory = "{Path.home()}"
        $Shortcut.Description = "JJMP3 local music player"
        $Shortcut.Save()
        """
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=False,
        capture_output=True,
    )
    return shortcut


def uninstall_linux() -> None:
    path = Path.home() / ".local" / "share" / "applications" / "jjmp3-web.desktop"
    path.unlink(missing_ok=True)
    for size_dir in ("256x256", "scalable"):
        for ext in (".png", ".svg"):
            icon = (
                Path.home()
                / ".local"
                / "share"
                / "icons"
                / "hicolor"
                / size_dir
                / "apps"
                / f"jjmp3{ext}"
            )
            icon.unlink(missing_ok=True)
    _try_update_desktop_database()


def uninstall_macos() -> None:
    shutil.rmtree(Path.home() / "Applications" / "JJMP3.app", ignore_errors=True)


def uninstall_windows() -> None:
    path = (
        Path(os.environ.get("APPDATA", ""))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "JJMP3.lnk"
    )
    path.unlink(missing_ok=True)


def install_launchers() -> Path | None:
    system = platform.system()
    if system == "Linux":
        return install_linux()
    if system == "Darwin":
        return install_macos()
    if system == "Windows":
        return install_windows()
    return None


def uninstall_launchers() -> None:
    system = platform.system()
    if system == "Linux":
        uninstall_linux()
    elif system == "Darwin":
        uninstall_macos()
    elif system == "Windows":
        uninstall_windows()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install JJMP3 OS launcher entries")
    parser.add_argument("action", choices=["install", "uninstall"])
    args = parser.parse_args(argv)
    if args.action == "install":
        dest = install_launchers()
        if dest:
            print(f"Launcher installed: {dest}")
        else:
            print("Unsupported platform; no launcher installed.", file=sys.stderr)
            return 1
    else:
        uninstall_launchers()
        print("Launchers removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
