# Daftar Aplikasi & File — Shiro / Sishin

Shiro dan Sishin bisa membuka software, folder, dan file di laptop Anda lewat chat atau suara.

## Desktop Anda (otomatis)

Semua shortcut dan file di **Desktop** terdaftar otomatis (read-only):

- Cursor, Excel, Word, Firefox, VirtualBox, Photopea, dll.
- File `.txt`, folder, dan shortcut `.lnk`
- **Shortcut Desktop tidak dipindah atau dihapus** — Shiro hanya membuka lewat Windows (`os.startfile`)

Ucapkan: `buka cursor`, `buka excel`, `buka photopea`, `buka db cukur asgar.txt`

## Cara menambah software baru (setelah install)

### Opsi 1 — Biarkan shortcut di Desktop (disarankan)

Cukup biarkan shortcut di Desktop — Shiro/Sishin akan mendeteksinya otomatis.

### Opsi 2 — Copy shortcut ke project (opsional)

1. Buka folder **`tambah_di_sini/`**
2. **Copy** (bukan pindah) shortcut `.lnk` ke folder itu
3. Ketik di chat: `scan ulang aplikasi`

### Opsi 3 — Edit JSON

Edit **`custom_apps.json`**:

```json
"nama_app": {
  "label": "Nama Tampilan",
  "type": "app",
  "path": "C:\\Program Files\\...\\app.exe",
  "aliases": ["nama lain", "singkatan"]
}
```

**type**: `app` | `folder` | `file`

## Perintah contoh

```
buka chrome
buka cursor
buka excel
buka photopea
buka folder voice_shiro
buka file db cukur asgar.txt
tolong buka spotify dong
```

## Scan otomatis

- **Desktop** (read-only, aman)
- Registry Windows (App Paths)
- Start Menu
- Documents, Downloads (`user_paths.json`)
- Folder `tambah_di_sini/` di project

Ketik `scan ulang aplikasi` atau `POST /api/voice/rescan` untuk refresh.

## API

- `GET /api/voice/apps` — daftar terdeteksi
- `POST /api/voice/rescan` — scan ulang
