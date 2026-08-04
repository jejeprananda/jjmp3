# JJMP3

CLI interaktif untuk mencari video YouTube dan mengunduh audio sebagai MP3 lewat [yt-dlp](https://github.com/yt-dlp/yt-dlp).

**Repo:** https://github.com/jejeprananda/jjmp3

## Prasyarat

- Python 3.10+
- [`pipx`](https://pipx.pypa.io/) (disarankan untuk install global)
- `yt-dlp` di PATH
- `ffmpeg` di PATH (untuk konversi MP3)

```bash
# Ubuntu / Debian
sudo apt install ffmpeg pipx
pipx ensurepath
# buka terminal baru setelah ensurepath

# yt-dlp (pilih salah satu)
pipx install yt-dlp
# atau: sudo apt install yt-dlp
```

## Install (disarankan)

Install langsung dari GitHub tanpa clone:

```bash
pipx install git+https://github.com/jejeprananda/jjmp3.git
```

Jalankan:

```bash
jjmp3
```

### Update

```bash
pipx reinstall jjmp3
# atau:
pipx install --force git+https://github.com/jejeprananda/jjmp3.git
```

### Uninstall

```bash
pipx uninstall jjmp3
```

## Install dari clone

```bash
git clone https://github.com/jejeprananda/jjmp3.git
cd jjmp3
pipx install .
```

Mode development (editable):

```bash
git clone https://github.com/jejeprananda/jjmp3.git
cd jjmp3
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
jjmp3
```

## Pemakaian

```bash
jjmp3
```

Alur:

1. Ketik query pencarian (typo ringan biasanya tetap ketemu lewat YouTube)
2. Pilih lagu dengan panah ↑↓ (bisa ketik untuk filter daftar)
3. File MP3 disimpan ke `~/Music/mp3Downloader`

## Catatan

Gunakan hanya untuk konten yang boleh Anda unduh (hak cipta / ToS YouTube). Tool ini adalah wrapper pribadi di atas yt-dlp.
