# Daftar Aplikasi & File — Shiro / Sishin

Shiro dan Sishin bisa membuka software, folder, dan file di laptop Anda lewat chat atau suara.

## Cara menambah software baru (setelah install)

### Opsi 1 — Taruh shortcut (COPY, jangan pindahkan!)

> **PENTING:** **Jangan pindahkan** shortcut dari Desktop ke sini. **Copy** saja (Ctrl+C → Ctrl+V).  
> Shiro AI **tidak pernah menghapus** shortcut Desktop — jika shortcut hilang, restore dari Recycle Bin atau buat ulang.

1. Buka folder **`tambah_di_sini/`** di sini
2. **Copy** (bukan pindah) shortcut (`.lnk`) aplikasi ke folder itu
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
- Registry aplikasi terpasang (Windows App Paths)
- Folder `tambah_di_sini/` dan `shortcuts/` **di dalam project saja**
- Documents, Downloads, dll. (bukan Desktop)

**Desktop tidak pernah di-scan atau disentuh** — shortcut Cursor, Chrome, dll. aman.

Cache scan disimpan lokal (tidak di-commit ke Git).

## API (opsional)

- `GET /api/voice/apps` — lihat daftar terdeteksi
- `POST /api/voice/rescan` — paksa scan ulang
