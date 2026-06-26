import requests

def test_voicevox(text, speaker=2):
    try:
        # 1. Buat query
        query = requests.post(
            f"http://localhost:50021/audio_query",
            params={"text": text, "speaker": speaker}
        )
        
        if query.status_code != 200:
            print(f"❌ Gagal query: {query.status_code}")
            return
        
        # 2. Generate suara
        audio = requests.post(
            f"http://localhost:50021/synthesis",
            params={"speaker": speaker},
            json=query.json()
        )
        
        if audio.status_code != 200:
            print(f"❌ Gagal synthesis: {audio.status_code}")
            return
        
        # 3. Simpan
        with open("test_voicevox.wav", "wb") as f:
            f.write(audio.content)
        
        print("✅ Suara berhasil: test_voicevox.wav")
        print("🔊 Dengarkan file test_voicevox.wav!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

# Test Shiro (Tohoku Zunko - Speaker ID 2)
test_voicevox("こんにちは、お兄さん！", speaker=2)

# Test Sishin (Zundamon - Speaker ID 1)
test_voicevox("お兄ちゃん、一緒に遊ぼう！", speaker=1)