# Sishin Live2D — Hierarki PNG & PSD siap import

Folder ini sudah disusun otomatis dari layer `Sishin.psd` kamu.

## File penting

| File / folder | Isi |
|---------------|-----|
| `01_Rambut_Belakang_Grup_Rambut_Belakang/` | PNG rambut belakang (urut 01–02) |
| `02_Badan_Grup_Badan/` | PNG badan (03) |
| `03_Kepala_Grup_Kepala/` | PNG wajah, mata, mulut (04–30) |
| `04_Rambut_Depan_Grup_Rambut_Depan/` | PNG poni & ahoge (31–32) |
| `hierarchy_manifest.json` | Data urutan + posisi layer (bbox) |

Angka di nama file (`01_`, `02_`…) = urutan **belakang → depan** (draw order).

---

## Cara import ke Cubism (disarankan: PSD asli)

**Opsi A — paling mudah (posisi otomatis pas):**

1. Buka **Cubism Editor PRO** → **New** → nama `Sishin`
2. **File → Import → Photoshop File**
3. Pilih: `d:\Downloads\Sishin.psd`
4. Setelah import, **drag layer ke 4 grup** di panel Parts:

```
Grup_Rambut_Belakang  ← folder 01
Grup_Badan            ← folder 02
Grup_Kepala           ← folder 03
Grup_Rambut_Depan     ← folder 04
```

Gunakan folder PNG di sini sebagai **panduan** nama & urutan drag.

**Opsi B — import PNG per file:**

1. Cubism → Import → Image files
2. Import **per folder**, urut `01` → `02` → `03` → `04`
3. Nama file sudah berurutan; posisi manual pakai `hierarchy_manifest.json` field `bbox`

---

## Setelah import — langkah berikutnya

1. **Cek draw order** — rambut belakang paling bawah, ahoge paling atas
2. **Mesh** tiap part (Model → Auto Mesh, density Medium)
3. **Deformer Kepala** → bind mata & mulut
4. Parameter: `ParamEyeLOpen`, `ParamEyeROpen`, `ParamMouthOpenY`
5. Export ke: `F:\Shiro_AI_V2\static\live2d\custom\sishin\`
6. Jalankan: `py scripts/install_custom_l2d.py`

---

## Kalau import PSD gagal — pakai PNG manual

Import PNG satu per satu **urut folder 01 → 04**, nama file sudah berurutan (`01_`, `02_`, … di dalam folder).

Posisi layer: lihat `hierarchy_manifest.json` field `bbox` (koordinat x,y dari canvas 1340×2980).

---

## Sub-grup opsional di Cubism (lebih rapi)

Di dalam **Grup_Kepala**, bisa buat sub-grup:

```
Grup_Kepala
├── Mata_Kiri   (Putih, Bola, Kelopak, Bulu mata kiri)
├── Mata_Kanan
├── Mulut       (Dalam, Bawah, Atas)
└── sisanya     (alis, hidung, rona, telinga, base wajah)
```

Ini opsional — bisa setelah mesh dasar jalan.
