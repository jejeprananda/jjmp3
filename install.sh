#!/usr/bin/env bash
# JJMP3 installer — asks for download directory, then installs via pipx.
set -euo pipefail

REPO_URL="${JJMP3_REPO_URL:-https://github.com/jejeprananda/jjmp3.git}"
DEFAULT_DIR="${HOME}/Music/mp3Downloader"
CONFIG_DIR="${HOME}/.config/jjmp3"
CONFIG_FILE="${CONFIG_DIR}/config.json"

echo "=== JJMP3 installer ==="
echo

if ! command -v pipx >/dev/null 2>&1; then
  echo "pipx tidak ditemukan. Install dulu, contoh:"
  echo "  sudo apt install pipx && pipx ensurepath"
  exit 1
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "Peringatan: yt-dlp belum di PATH. Install sebelum menjalankan jjmp3."
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Peringatan: ffmpeg belum di PATH. Install sebelum menjalankan jjmp3."
fi

echo "Di mana MP3 akan disimpan?"
printf "Download directory [%s]: " "$DEFAULT_DIR"
read -r DOWNLOAD_DIR
DOWNLOAD_DIR="${DOWNLOAD_DIR:-$DEFAULT_DIR}"

# Expand ~
DOWNLOAD_DIR="${DOWNLOAD_DIR/#\~/$HOME}"

mkdir -p "$DOWNLOAD_DIR"
mkdir -p "$CONFIG_DIR"

# Minimal JSON without requiring python during install prompt
python3 - "$CONFIG_FILE" "$DOWNLOAD_DIR" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
download = str(Path(sys.argv[2]).expanduser().resolve())
Path(download).mkdir(parents=True, exist_ok=True)
data = {}
if path.is_file():
    try:
        data = json.loads(path.read_text())
    except Exception:
        data = {}
data["download_dir"] = download
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n")
print(f"Config disimpan: {path}")
print(f"Download dir: {download}")
PY

echo
echo "Menginstall jjmp3 dari GitHub..."
pipx install --force "$REPO_URL"

echo
echo "Memasang launcher di menu aplikasi OS..."
if command -v jjmp3-desktop >/dev/null 2>&1; then
  jjmp3-desktop install || true
else
  echo "  (lewati — jjmp3-desktop belum di PATH; jalankan: jjmp3-desktop install)"
fi

echo
echo "Selesai."
echo "  Web UI (menu app / Spotlight / Start): cari \"JJMP3\""
echo "  CLI download: jjmp3"
echo "  Tutup tab browser = app berhenti otomatis"
echo "Ubah folder download lewat Settings di Web UI atau /setting di CLI."
