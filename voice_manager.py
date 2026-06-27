# voice_manager.py (tanpa VITS)
import asyncio
import logging
import os
import uuid
import edge_tts
import requests

logger = logging.getLogger(__name__)

class VoiceManager:
    def __init__(self, temp_dir="tmp", voicevox_url="http://localhost:50021"):
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
        self.voicevox_url = voicevox_url
        self.voicevox_available = self._check_voicevox()
        self.speakers = {"shiro": 107, "sishin": 8}
        self.voicevox_params = {
            "shiro": {"speedScale": 0.85, "pitchScale": 1.0, "intonationScale": 1.1},
            "sishin": {"speedScale": 0.9, "pitchScale": 1.2, "intonationScale": 1.2},
        }
        self.romaji_keywords = [
            "konnichiwa", "ohayou", "konbanwa", "arigatou", "gomen",
            "daisuki", "sayonara", "onii-chan", "onee-san", "genki",
            "kawaii", "sugoi", "yatta", "itadakimasu", "gochisousama",
        ]
        if self.voicevox_available:
            logger.info("Voicevox active at %s", self.voicevox_url)
        else:
            logger.info("Voicevox not active, using Edge TTS fallback")

    def _check_voicevox(self):
        try:
            response = requests.get(f"{self.voicevox_url}/version", timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def _detect_japanese(self, text):
        for char in text:
            code = ord(char)
            if 0x3040 <= code <= 0x30FF or 0x4E00 <= code <= 0x9FFF:
                return True
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.romaji_keywords)

    async def generate(self, text, karakter="shiro", bahasa="id"):
        if self._detect_japanese(text) or self.voicevox_available:
            if self.voicevox_available:
                try:
                    return await self._generate_voicevox(text, karakter)
                except Exception:
                    logger.exception("Voicevox failed, fallback Edge TTS")
        return await self._generate_edge_tts(text, "jp" if self._detect_japanese(text) else "id")

    def _voicevox_query(self, text, speaker, params):
        query_url = f"{self.voicevox_url}/audio_query"
        query_payload = {
            "text": text,
            "speaker": speaker,
            "speedScale": params.get("speedScale", 0.85),
            "pitchScale": params.get("pitchScale", 1.0),
            "intonationScale": params.get("intonationScale", 1.1),
        }
        return requests.post(query_url, params=query_payload, timeout=30)

    def _voicevox_synthesis(self, speaker, query_json):
        synthesis_url = f"{self.voicevox_url}/synthesis"
        return requests.post(
            synthesis_url,
            params={"speaker": speaker},
            json=query_json,
            timeout=60,
        )

    async def _generate_voicevox(self, text, karakter):
        try:
            speaker = self.speakers.get(karakter, 107)
            params = self.voicevox_params.get(karakter, {})
            query_res = await asyncio.to_thread(self._voicevox_query, text, speaker, params)
            if query_res.status_code != 200:
                logger.warning("Voicevox query failed: %s", query_res.status_code)
                return await self._generate_edge_tts(text, "jp")
            audio_res = await asyncio.to_thread(
                self._voicevox_synthesis, speaker, query_res.json()
            )
            if audio_res.status_code != 200:
                logger.warning("Voicevox synthesis failed: %s", audio_res.status_code)
                return await self._generate_edge_tts(text, "jp")
            file_name = f"{karakter}_voicevox_{uuid.uuid4().hex}.wav"
            file_path = os.path.join(self.temp_dir, file_name)
            with open(file_path, "wb") as f:
                f.write(audio_res.content)
            return file_path
        except Exception as exc:
            logger.exception("Voicevox error: %s", exc)
            return await self._generate_edge_tts(text, "jp")

    async def _generate_edge_tts(self, text, bahasa="id"):
        try:
            voice = "ja-JP-NanamiNeural" if bahasa == "jp" else "id-ID-GadisNeural"
            communicate = edge_tts.Communicate(text, voice)
            file_name = f"edge_{bahasa}_{uuid.uuid4().hex}.mp3"
            file_path = os.path.join(self.temp_dir, file_name)
            await communicate.save(file_path)
            return file_path
        except Exception as exc:
            logger.exception("EdgeTTS error: %s", exc)
            return None