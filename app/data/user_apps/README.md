# Daftar Aplikasi & File — Shiro / Sishin

Shiro dan Sishin bisa membuka software, folder, dan file di laptop Anda lewat chat atau suara.

## Cara menambah software baru (setelah install)

### Opsi 1 — Taruh shortcut (paling mudah)
1. Buka folder **`tambah_di_sini/`** di sini
2. Copy shortcut (`.lnk`) aplikasi baru ke folder itu
3. Restart server Shiro AI **atau** ketik di chat: `scan ulang aplikasi`
4. Ucapkan: `buka [nama aplikasi]`

### Opsi 2 — Edit JSON
Edit file **`custom_apps.json`** di folder ini:

```json
"nama_app": {
  "label": "Nama Tampilan",
  "type": "app",
  "path": "C:\\Program Files\\...\\app.exe",
  "aliases": ["nama lain", "singkatan"]
}
```

**type** bisa:
- `app` — program (.exe)
- `folder` — folder/direktori
- `file` — dokumen, gambar, video, dll.

### Opsi 3 — Folder untuk di-scan otomatis
Edit **`app/data/user_paths.json`** — tambahkan path folder di `extra_folders` atau `scan_roots`.

## Perintah contoh

```
buka chrome
buka cursor
buka folder documents
buka file laporan.pdf
tolong buka spotify dong
```

## Scan otomatis

Saat server jalan, Shiro AI memindai:
- Menu Start Windows
- Desktop
- Registry aplikasi terpasang
- Folder Desktop, Documents, Downloads (lihat `user_paths.json`)
- Semua isi folder `tambah_di_sini/` dan `shortcuts/`

Cache scan disimpan lokal (tidak di-commit ke Git).

## API (opsional)

- `GET /api/voice/apps` — lihat daftar terdeteksi
- `POST /api/voice/rescan` — paksa scan ulang
