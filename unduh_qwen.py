import os
import requests
import time
from tqdm import tqdm

url = "https://hf-mirror.com/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"
filename = "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"

print("📡 [SHIRO SYSTEM] Mengaktifkan Mode Pengawal Otomatis Anti-Timeout!")

while True:
    existing_size = os.path.getsize(filename) if os.path.exists(filename) else 0
    headers = {'Range': f'bytes={existing_size}-'} if existing_size > 0 else {}
    
    if existing_size > 0:
        print(f"\n🔄 [SHIRO] Mengunci posisi aman di {existing_size / (1024**3):.2f} GB. Menyambung sisa data...")
    else:
        print("\n🚀 [SHIRO] Memulai unduhan baru...")

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        # Jika server mengembalikan kode 416, artinya file sebenarnya sudah selesai terunduh penuh!
        if response.status_code == 416:
            print("\n✨ [HOREEE] File ternyata sudah selesai terunduh sempurna 100%!")
            break
            
        total_size = int(response.headers.get('content-length', 0)) + existing_size
        mode = 'ab' if existing_size > 0 else 'wb'
        
        with open(filename, mode) as f, tqdm(
            total=total_size,
            initial=existing_size,
            unit='B',
            unit_scale=True,
            desc="📥 Progress Qwen 7B"
        ) as bar:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))
                    
        # Jika berhasil keluar dari loop dengan sukses tanpa eror
        if os.path.getsize(filename) >= total_size:
            print("\n✨ [HOREEE] Akhirnya sukses 100%! Perjuangan Kakak Shin berhasil!")
            break

    except (requests.exceptions.RequestException, Exception) as e:
        print(f"\n⚠️ [INFO SHIRO] Internet kedip sesaat ({e}). Jangan khawatir, Shiro akan mencoba menyambung ulang otomatis dalam 5 detik...")
        time.sleep(5)