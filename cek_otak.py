import os

folder_proyek = r"F:\Shiro_AI_V2"
file_1 = "qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf"
file_2 = "qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf"

print("🔍 [SHIRO SYSTEM] Sedang memindai otak Princess Sishin...")

if os.path.exists(os.path.join(folder_proyek, file_1)) and os.path.exists(os.path.join(folder_proyek, file_2)):
    print("✅ [SUKSES] Kedua bagian otak terdeteksi dan siap dirakit!")
    print("💖 Princess Sishin sudah tidak sabar untuk mulai berpikir!")
else:
    print("❌ [WARNING] Masih ada bagian yang hilang, Kakak Shin sayang!")