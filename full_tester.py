import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.chdir(BASE_DIR)

print("=" * 50)
print("TEST CEPAT SHIRO AI")
print("=" * 50)

pesan = "sishin, halo!"
print(f"Pesan: '{pesan}'")

try:
    from app.chat import jawab_shiro

    jawaban, status = jawab_shiro(pesan, preferred_karakter="sishin")
    print(f"Karakter: {jawaban.get('karakter')}")
    print(f"Respon: {jawaban.get('text', '')[:100]}...")
    print(f"Status: affection={status.get('affection')}")
except Exception as e:
    print(f"ERROR: {e}")
