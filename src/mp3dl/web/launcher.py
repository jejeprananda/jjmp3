"""Desktop launcher: start Web UI, open browser, exit when UI closes."""

from __future__ import annotations

import socket
import sys
import threading
import webbrowser

import uvicorn

from mp3dl.config import config_exists, get_web_port
from mp3dl.web import lifecycle
from mp3dl.web.app import create_app


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


def _app_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def run_web_server(*, open_browser: bool = True) -> None:
    """Start uvicorn; stop when all browser tabs disconnect."""
    from mp3dl.config import DEFAULT_DOWNLOAD_DIR, set_download_dir

    if not config_exists():
        if sys.stdin.isatty():
            from mp3dl.cli import run_settings

            if not run_settings(first_run=True):
                print("Setup cancelled.", file=sys.stderr)
                raise SystemExit(1)
        else:
            set_download_dir(DEFAULT_DOWNLOAD_DIR)

    port = get_web_port()
    url = _app_url(port)

    if _port_open("127.0.0.1", port):
        if open_browser:
            webbrowser.open(url)
        print(f"JJMP3 already running at {url}")
        return

    config = uvicorn.Config(
        create_app(),
        host="127.0.0.1",
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    lifecycle.set_shutdown_callback(lambda: setattr(server, "should_exit", True))
    lifecycle.start_watchdog()

    if open_browser:
        def _open() -> None:
            webbrowser.open(url)

        threading.Timer(0.6, _open).start()

    print(f"JJMP3 Web UI at {url} — close the browser tab to quit.")
    server.run()


def main() -> None:
    run_web_server(open_browser=True)


if __name__ == "__main__":
    main()
