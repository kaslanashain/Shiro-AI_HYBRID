# voice_manager.py - FINAL VERSION
# ============================================================
# VOICEVOX SPEAKER ID REFERENCE:
# - Shiro (Tohoku Zunko): ID 107 (Normal)
# - Sishin (Kasukabe Tsumugi): ID 8 (Normal)
# ============================================================

import os
import uuid
import asyncio
import edge_tts
import requests
import json

class VoiceManager:
    def __init__(self, temp_dir="tmp"):
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # ============================================================
        # VOICEVOX CONFIGURATION
        # ============================================================
        self.voicevox_url = "http://localhost:50021"
        self.voicevox_available = self._check_voicevox()
        
        # Speaker ID berdasarkan hasil query /speakers
        self.speakers = {
            "shiro": 107,   # Tohoku Zunko (Normal)
            "sishin": 8,    # Kasukabe Tsumugi (Normal)
        }
        
        # ============================================================
        # VOICEVOX PARAMETERS (Speed, Pitch, Intonation)
        # ============================================================
        self.voicevox_params = {
            "shiro": {
                "speedScale": 0.85,      # Lebih lambat 15%
                "pitchScale": 1.0,       # Normal
                "intonationScale": 1.1   # Lebih ekspresif
            },
            "sishin": {
                "speedScale": 0.9,       # Sedikit lebih cepat
                "pitchScale": 1.2,       # Lebih tinggi (imut)
                "intonationScale": 1.2   # Sangat ekspresif
            }
        }
        
        # ============================================================
        # ROMAJI KEYWORDS FOR JAPANESE DETECTION
        # ============================================================
        self.romaji_keywords = [
            'konnichiwa', 'ohayou', 'konbanwa', 'arigatou', 'gomen',
            'daisuki', 'sayonara', 'onii-chan', 'onee-san', 'genki',
            'kawaii', 'sugoi', 'yatta', 'itadakimasu', 'gochisousama',
            'oishii', 'takai', 'yasui', 'samui', 'atsui', 'tanoshii',
            'ganbatte', 'omedetou', 'otsukaresama', 'irasshaimase'
        ]
        
        # ============================================================
        # INITIALIZATION STATUS
        # ============================================================
        if self.voicevox_available:
            print("[VoiceManager] Voicevox active (Japanese)")
            print(f"   Shiro: Tohoku Zunko (ID: {self.speakers['shiro']})")
            print(f"   Sishin: Kasukabe Tsumugi (ID: {self.speakers['sishin']})")
        else:
            print("[VoiceManager] Voicevox not active, fallback to Edge TTS")

    # ============================================================
    # CHECK VOICEVOX AVAILABILITY
    # ============================================================
    def _check_voicevox(self):
        try:
            response = requests.get(f"{self.voicevox_url}/version", timeout=2)
            return response.status_code == 200
        except:
            return False

    # ============================================================
    # DETECT JAPANESE LANGUAGE (Kanji, Kana, or Romaji)
    # ============================================================
    def _detect_japanese(self, text):
        """Deteksi teks Jepang (Hiragana/Katakana/Kanji) atau Romaji"""
        # Cek karakter Jepang
        for char in text:
            code = ord(char)
            # Hiragana: 0x3040-0x309F
            # Katakana: 0x30A0-0x30FF
            # Kanji: 0x4E00-0x9FFF
            if 0x3040 <= code <= 0x30FF or 0x4E00 <= code <= 0x9FFF:
                return True
        # Cek kata Romaji
        text_lower = text.lower()
        for keyword in self.romaji_keywords:
            if keyword in text_lower:
                return True
        return False

    # ============================================================
    # CORE GENERATE FUNCTION
    # ============================================================
    async def generate(self, text, karakter="shiro", bahasa="id"):
        """Generate voice based on language detection"""
        detected = self._detect_japanese(text)
        
        if detected:
            if self.voicevox_available:
                return await self._generate_voicevox(text, karakter)
            else:
                return await self._generate_edge_tts(text, "jp")
        else:
            return await self._generate_edge_tts(text, "id")

    # ============================================================
    # VOICEVOX GENERATION (Japanese)
    # ============================================================
    async def _generate_voicevox(self, text, karakter):
        """Generate Japanese voice using Voicevox"""
        try:
            speaker = self.speakers.get(karakter, 107)
            params = self.voicevox_params.get(karakter, {})
            
            # Build audio query with parameters
            query_url = f"{self.voicevox_url}/audio_query"
            query_payload = {
                "text": text,
                "speaker": speaker,
                "speedScale": params.get("speedScale", 0.85),
                "pitchScale": params.get("pitchScale", 1.0),
                "intonationScale": params.get("intonationScale", 1.1)
            }
            
            query_res = requests.post(query_url, params=query_payload)
            
            if query_res.status_code != 200:
                print(f"[Voicevox] Query failed: {query_res.status_code}")
                return await self._generate_edge_tts(text, "jp")
            
            # Generate speech
            synthesis_url = f"{self.voicevox_url}/synthesis"
            audio_res = requests.post(
                synthesis_url,
                params={"speaker": speaker},
                json=query_res.json()
            )
            
            if audio_res.status_code != 200:
                print(f"[Voicevox] Synthesis failed: {audio_res.status_code}")
                return await self._generate_edge_tts(text, "jp")
            
            # Save audio file
            file_name = f"{karakter}_voicevox_{uuid.uuid4().hex}.wav"
            file_path = os.path.join(self.temp_dir, file_name)
            
            with open(file_path, "wb") as f:
                f.write(audio_res.content)
            
            print(f"[Voicevox] Voice ready: {file_name} (Speaker ID: {speaker})")
            return file_path
            
        except Exception as e:
            print(f"[Voicevox] Error: {e}")
            return await self._generate_edge_tts(text, "jp")

    # ============================================================
    # EDGE TTS GENERATION (Indonesian or Fallback Japanese)
    # ============================================================
    async def _generate_edge_tts(self, text, bahasa="id"):
        """Generate voice using Edge TTS (Indonesian or Japanese fallback)"""
        try:
            if bahasa == "jp":
                voice = "ja-JP-NanamiNeural"
                label = "Japanese (fallback)"
            else:
                voice = "id-ID-GadisNeural"
                label = "Indonesian"
            
            communicate = edge_tts.Communicate(text, voice)
            
            file_name = f"edge_{bahasa}_{uuid.uuid4().hex}.mp3"
            file_path = os.path.join(self.temp_dir, file_name)
            await communicate.save(file_path)
            
            print(f"[EdgeTTS] Voice ready: {file_name} ({label})")
            return file_path
            
        except Exception as e:
            print(f"[EdgeTTS] Error: {e}")
            return None