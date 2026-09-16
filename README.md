# JJMP3

**Versi saat ini: `0.4.1`**

JJMP3 adalah aplikasi **open source** untuk mencari lagu di YouTube, mengunduh audio sebagai MP3, lalu memutarnya dari folder lokal — lewat **CLI** atau **Web UI** bergaya music player.

**Repo:** https://github.com/jejeprananda/jjmp3  
**Lisensi:** [MIT](LICENSE)

---

## Apa gunanya?

| Mode | Kegunaan |
|------|----------|
| **CLI** (`jjmp3`) | Cari YouTube → pilih → download MP3 ke folder yang kamu tentukan |
| **Web UI** (`jjmp3-web`) | Library lokal, search & download, explorer file, playlist JSON, player dengan shuffle/repeat |
| **Desktop launcher** | Muncul di pencarian aplikasi OS (Linux / macOS / Windows) |

Web UI **bukan streaming YouTube**. Player hanya memutar file MP3 yang sudah ada di folder download. Search dipakai untuk **mendownload**; jika lagu sudah ada (video_id atau judul sama), muncul badge *Already downloaded* dan download dicegah.

Tutup tab browser = server Web UI berhenti otomatis.

---

## Bahasa & stack

| Layer | Teknologi |
|-------|-----------|
| Bahasa utama | **Python ≥ 3.10** |
| CLI | Rich, InquirerPy |
| Web server | FastAPI + Uvicorn |
| Frontend | HTML / CSS / Vanilla JS (ES modules), GSAP (vendored) |
| Download audio | **yt-dlp** + **ffmpeg** |
| Data | JSON di folder download (`library.json`, `playlists.json`) + config di `~/.config/jjmp3/` |

Tidak ada React/Vite — frontend di-package bersama Python agar `pipx install` tetap sederhana.

---

## Prasyarat

- Python 3.10+
- [`pipx`](https://pipx.pypa.io/) (disarankan untuk install global)
- `ffmpeg` di PATH
- `yt-dlp` (biasanya ikut terpasang sebagai dependency Python; pastikan juga bisa di PATH jika CLI standalone)

```bash
# Ubuntu / Debian
sudo apt install ffmpeg pipx
pipx ensurepath
# buka terminal baru setelah ensurepath
```

---

## Install

### Cara cepat (disarankan)

```bash
curl -fsSL https://raw.githubusercontent.com/jejeprananda/jjmp3/main/install.sh | bash
```

Installer akan:

1. Menanyakan folder download (default `~/Music/mp3Downloader`)
2. Menyimpan config ke `~/.config/jjmp3/config.json`
3. Memasang `jjmp3` lewat pipx
4. Memasang launcher OS (`jjmp3-desktop install`)

### pipx langsung

```bash
pipx install git+https://github.com/jejeprananda/jjmp3.git
jjmp3-desktop install   # opsional: daftar di menu aplikasi
```

### Dari clone (development)

```bash
git clone https://github.com/jejeprananda/jjmp3.git
cd jjmp3
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
jjmp3-desktop install
```

Atau: `bash install.sh` / `pipx install .`

### Perintah yang tersedia setelah install

| Perintah | Fungsi |
|----------|--------|
| `jjmp3` | CLI interaktif (download) |
| `jjmp3 web` | Sama dengan `jjmp3-web` |
| `jjmp3-web` | Jalankan Web UI + buka browser |
| `jjmp3-desktop install` | Pasang launcher ke menu OS |
| `jjmp3-desktop uninstall` | Hapus launcher |

Cari **"JJMP3"** di menu aplikasi Linux, Spotlight/Launchpad macOS, atau Start Menu Windows.

---

## Cara pakai

### CLI

```bash
jjmp3
```

1. Ketik query pencarian (atau `/setting` / `/update`)
2. Pilih hasil dengan panah ↑↓ (bisa ketik untuk filter)
3. MP3 tersimpan di folder download (checklist + progress)

Perintah khusus di prompt:

| Input | Aksi |
|-------|------|
| `/setting` | Ubah folder download |
| `/update` | Cek & install update dari GitHub via pipx |
| Enter kosong | Keluar |

### Web UI

```bash
jjmp3-web
# atau
jjmp3 web
```

Buka `http://127.0.0.1:8765` (hanya localhost).

| View | Fungsi |
|------|--------|
| **Library** | Daftar & putar semua MP3 di folder download |
| **Search** | Cari YouTube → klik = download. Sudah ada → play lokal |
| **Explorer** | File browser folder yang sama (hapus file, tambah ke playlist) |
| **Playlists** | Buat / rename / hapus playlist; editor visual + JSON |
| **Settings** | Folder download, cek update, lihat versi |

Kontrol player: play/pause, prev/next, shuffle, repeat (off/one/all), seek, volume. Shortcut: `Space`, `←` / `→` (saat tidak sedang mengetik).

**Lifecycle:** tab browser mengirim heartbeat; tutup tab terakhir → proses server berhenti.

---

## Settings & konfigurasi

### File config

`~/.config/jjmp3/config.json`

```json
{
  "download_dir": "/home/you/Music/mp3Downloader",
  "web_port": 8765,
  "cache_dir": "/home/you/.cache/jjmp3",
  "cache_max_age_days": 7
}
```

| Key | Default | Keterangan |
|-----|---------|------------|
| `download_dir` | `~/Music/mp3Downloader` | Satu-satunya folder library / explorer / playlist |
| `web_port` | `8765` | Port Web UI (localhost) |
| `cache_dir` | `~/.cache/jjmp3` | Legacy; stream-cache tidak lagi dipakai Web UI |
| `cache_max_age_days` | `7` | Legacy |

Ubah `download_dir` lewat:

- Web UI → **Settings** → Apply
- CLI → `/setting`

### Isi folder download

```
{download_dir}/
  Lagu.mp3
  covers/{video_id}.jpg     # thumbnail (opsional)
  library.json              # indeks video_id ↔ file (otomatis)
  playlists.json            # playlist user
```

`playlists.json` contoh:

```json
{
  "version": 1,
  "playlists": [
    {
      "id": "pl_workout",
      "name": "Workout",
      "tracks": ["Song A.mp3", "Song B.mp3"]
    }
  ]
}
```

Track diacu dengan **nama file relatif**, bukan YouTube ID. Editor di Web UI bisa edit visual atau JSON mentah.

---

## Update & uninstall

### Update

- Web UI → **Settings** → **Check for updates** → **Install update**
- CLI: `/update`
- Manual:

```bash
pipx install --force git+https://github.com/jejeprananda/jjmp3.git
jjmp3-desktop install
```

Setelah update, **restart** Web UI agar proses memakai kode baru.

### Uninstall

```bash
jjmp3-desktop uninstall
pipx uninstall jjmp3
# opsional:
# rm -rf ~/.config/jjmp3
```

---

## Development & kontribusi

JJMP3 **open source** — kontribusi welcome.

### Setup lokal

```bash
git clone https://github.com/jejeprananda/jjmp3.git
cd jjmp3
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

### Struktur singkat

```
src/mp3dl/
  cli.py              # CLI entry
  download.py         # yt-dlp → MP3
  search.py           # ytsearch
  update.py           # cek/install update GitHub
  desktop.py          # launcher OS
  config.py           # ~/.config/jjmp3
  web/
    app.py            # FastAPI
    launcher.py       # jjmp3-web + lifecycle shutdown
    library.py        # scan folder, index, Range serve
    playlists_store.py
    jobs.py           # download background
    static/           # Web UI
tests/
```

### Ide kontribusi

- Bugfix & regression tests
- UX Web UI / aksesibilitas
- Metadata ID3 / cover art lebih baik
- Packaging (AppImage, Flatpak, dll.)
- Dokumentasi & terjemahan

Alur: fork → branch → PR ke `main`. Jelaskan *mengapa* perubahan itu berguna. Jaga agar CLI dan Web UI tetap bisa diinstall lewat pipx tanpa build frontend terpisah.

### Tes

```bash
pytest -q
```

---

## Catatan hukum

Gunakan hanya untuk konten yang boleh Anda unduh (hak cipta / ToS YouTube). JJMP3 adalah wrapper pribadi di atas [yt-dlp](https://github.com/yt-dlp/yt-dlp).

---

## Changelog ringkas

| Versi | Catatan |
|-------|---------|
| **0.4.1** | Dedup download by title, progress UI lebih stabil, README lengkap, versi di UI |
| **0.4.0** | Local library player, playlist JSON, OS launcher, icon, Settings → Updates |
| **0.3.x** | Web streaming + SQLite playlists (diganti di 0.4) |

---

Dibuat dengan ☕ · MIT License · [Issues](https://github.com/jejeprananda/jjmp3/issues)
