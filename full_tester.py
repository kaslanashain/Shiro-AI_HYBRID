# full_tester.py
import os
import sys

# ===== TAMBAHKAN PATH KE FOLDER UTAMA =====
BASE_DIR = r"F:\Shiro_AI_V2"  # ← PASTIKAN PATH INI BENAR!
sys.path.insert(0, BASE_DIR)

# ===== UBAH WORKING DIRECTORY =====
os.chdir(BASE_DIR)

print("="*50)
print("🧪 TEST CEPAT SHIRO AI")
print("="*50)
print(f"📂 Working Directory: {os.getcwd()}")
print(f"📂 Python Path: {sys.path[:2]}")

# ===== TEST SEDERHANA =====
pesan = "sishin, halo!"
print(f"\n📝 Pesan: '{pesan}'")

try:
    # ===== IMPORT DARI MAIN.PY =====
    from main import jawab_shiro
    
    jawaban, status = jawab_shiro(pesan)
    print(f"✅ Karakter: {jawaban.get('karakter')}")
    print(f"✅ Respon: {jawaban.get('text', '')[:100]}...")
    print(f"✅ Status: affection={status.get('affection')}")
    
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("   📁 Pastikan file 'main.py' ada di F:\\Shiro_AI_V2\\")
    
except Exception as e:
    print(f"❌ ERROR: {e}")