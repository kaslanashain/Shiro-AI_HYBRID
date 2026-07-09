# Live2D — Shiro & Sishin

| Karakter | Default | Opsi Live2D sample | Custom upload |
|----------|---------|-------------------|---------------|
| **Shiro** | Ekspresi PNG | Haru | `custom/shiro/` |
| **Sishin** | Ekspresi PNG | Hiyori | `custom/sishin/` |

## Sample models (sudah terpasang)

| Model | Path |
|-------|------|
| Haru (untuk Shiro) | `shiro/Haru.model3.json` |
| Hiyori (untuk Sishin) | `samples/hiyori/Hiyori.model3.json` |

Pasang ulang sample dari internet:
```bash
py scripts/install_live2d_samples.py
py scripts/setup_live2d_layout.py
```

## Upload model custom (buat sendiri)

1. Export dari Cubism ke folder:
   - Shiro → `custom/shiro/`
   - Sishin → `custom/sishin/`
2. Lihat `README.txt` di masing-masing folder
3. Jalankan:
   ```bash
   py scripts/install_custom_l2d.py
   ```
4. Refresh browser — opsi **Custom (Upload)** muncul di Wardrobe

## Layout folder

```
static/live2d/
├── shiro/           Haru sample (+ motions)
├── samples/hiyori/  Hiyori sample
├── custom/
│   ├── shiro/       ← upload model Shiro custom
│   └── sishin/      ← upload model Sishin custom
└── _archive/        arsip lama
```
