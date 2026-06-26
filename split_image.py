# split_image.py
# Potong gambar JPEG/PNG menjadi 2 bagian (kiri = Shiro, kanan = Sishin)

from PIL import Image
import os

# ==========================================
# KONFIGURASI
# ==========================================
# Ganti dengan nama file gambar Anda
image_path = "static/images/gambar_utama.jpeg"  # ← GANTI NAMA FILE!

output_dir = "static/images/"

# ==========================================
# PROSES POTONG
# ==========================================
def split_image():
    """Potong gambar menjadi 2 bagian dan simpan sebagai PNG"""
    
    # Cek apakah file ada
    if not os.path.exists(image_path):
        print(f"\n❌ ERROR: File tidak ditemukan!")
        print(f"📁 Path: {image_path}")
        print(f"\n📝 Ganti nama file di variable 'image_path'")
        print(f"   Contoh: image_path = 'static/images/nama_file_anda.jpeg'")
        print(f"\n📂 Pastikan file gambar ada di folder: static/images/")
        return
    
    try:
        # Buka gambar
        img = Image.open(image_path)
        width, height = img.size
        
        print(f"\n📐 Ukuran gambar: {width} x {height} px")
        print(f"📁 File: {image_path}")
        
        # Potong menjadi 2 bagian (kiri & kanan)
        left_half = img.crop((0, 0, width//2, height))
        right_half = img.crop((width//2, 0, width, height))
        
        # Simpan sebagai PNG
        left_path = os.path.join(output_dir, "shiro.png")
        right_path = os.path.join(output_dir, "sishin.png")
        
        left_half.save(left_path)
        right_half.save(right_path)
        
        print(f"\n✅ GAMBAR BERHASIL DIPOTONG!")
        print(f"   Shiro (kiri): {left_path}")
        print(f"   Sishin (kanan): {right_path}")
        print(f"\n   Sekarang refresh browser (Ctrl+F5) untuk melihat perubahan!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"\n💡 Tips:")
        print(f"   1. Pastikan Pillow terinstall: pip install Pillow")
        print(f"   2. Pastikan file gambar ada di folder static/images/")
        print(f"   3. Pastikan nama file di kode benar")

# ==========================================
# JALANKAN
# ==========================================
if __name__ == "__main__":
    print("="*50)
    print("   SHIRO AI - SPLIT IMAGE")
    print("="*50)
    split_image()
    print("\n" + "="*50)