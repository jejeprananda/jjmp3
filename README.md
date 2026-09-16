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

## Install (disarankan) — dengan tanya download folder

```bash
curl -fsSL https://raw.githubusercontent.com/jejeprananda/jjmp3/main/install.sh | bash
```

Installer akan menanyakan **download directory** (default `~/Music/mp3Downloader`), menyimpan config ke `~/.config/jjmp3/config.json`, lalu memasang `jjmp3` lewat pipx.

### Atau pipx langsung (tanpa script)

```bash
pipx install git+https://github.com/jejeprananda/jjmp3.git
jjmp3
```

Saat pertama kali dijalankan, JJMP3 akan menanyakan folder download jika belum ada config.

Jalankan:

```bash
jjmp3
```

### Update

Di dalam app, ketik:

```text
/update
```

Atau manual:

```bash
pipx reinstall jjmp3
# atau:
pipx install --force git+https://github.com/jejeprananda/jjmp3.git
```

### Uninstall

```bash
pipx uninstall jjmp3
# opsional hapus config:
# rm -rf ~/.config/jjmp3
```

## Install dari clone

```bash
git clone https://github.com/jejeprananda/jjmp3.git
cd jjmp3
bash install.sh
# atau: pipx install .
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

### CLI (downloader)

```bash
jjmp3
```

Alur:

1. Ketik query pencarian (typo ringan biasanya tetap ketemu lewat YouTube)
2. Ketik `/setting` untuk mengubah folder download
3. Ketik `/update` untuk cek & update ke versi terbaru
4. Pilih lagu dengan panah ↑↓ (bisa ketik untuk filter daftar)
5. File MP3 disimpan ke folder yang dikonfigurasi (ada checklist + progress bar)

### Web UI (local music player)

```bash
jjmp3 web
# atau
jjmp3-web
```

Membuka browser di `http://127.0.0.1:8765` (local-only). **Tutup tab browser = server berhenti otomatis.**

Setelah install via `install.sh`, JJMP3 muncul di launcher OS:

- **Linux** — menu aplikasi (GNOME/KDE, dll.)
- **macOS** — Spotlight / Launchpad (`Applications/JJMP3.app`)
- **Windows** — Start Menu

Pasang / hapus launcher manual:

```bash
jjmp3-desktop install
jjmp3-desktop uninstall
```

Fitur Web UI:

- **Library** — putar MP3 lokal dari folder download
- **Search** — cari YouTube, klik untuk download (badge *Already downloaded* jika sudah ada)
- **Explorer** — kelola file MP3 di folder download
- **Playlist** — disimpan sebagai `playlists.json` di folder download (+ editor JSON)
- **Settings** — ubah folder download
- **Shuffle**, repeat (off / one / all), volume, seek

Config (opsional) di `~/.config/jjmp3/config.json`:

```json
{
  "download_dir": "~/Music/mp3Downloader",
  "web_port": 8765
}
```

## Catatan

Gunakan hanya untuk konten yang boleh Anda unduh (hak cipta / ToS YouTube). Tool ini adalah wrapper pribadi di atas yt-dlp.
