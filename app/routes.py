import logging
import os
import requests  # ⬅️ TAMBAHAN: untuk panggil API cuaca dari backend
from flask import jsonify, render_template, request, send_file
from app import config
from app.chat import (
    apply_sawer, deskripsi_gambar, jawab_shiro,
    check_initiative, check_events, get_mood,
)
from app.db import muat_status
from app.tts import generate_speech, cleanup_old_tts_files

logger = logging.getLogger(__name__)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

def _chat_payload(data):
    pesan = (data.get("message") or "").strip()
    karakter = (data.get("karakter") or "shiro").strip().lower()
    if karakter not in ("shiro", "sishin"):
        karakter = "shiro"
    return pesan, karakter

def register_routes(app):
    """Daftarkan semua HTTP routes (TANPA SocketIO)"""

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/chat", methods=["POST"])
    def chat():
        data = request.get_json(silent=True) or {}
        pesan, karakter = _chat_payload(data)
        if not pesan:
            return jsonify({"error": "Pesan kosong"}), 400
        jawaban_data, status = jawab_shiro(pesan, preferred_karakter=karakter)
        return jsonify({
            "reply": jawaban_data.get("text", ""),
            "suara": jawaban_data.get("suara", jawaban_data.get("text", "")),
            "status": status,
            "karakter": jawaban_data.get("karakter", karakter),
        })

    @app.route("/status", methods=["GET"])
    def get_status():
        return jsonify(muat_status())

    @app.route("/initiative", methods=["GET"])
    def initiative():
        result = check_initiative()
        if result:
            return jsonify(result)
        return jsonify(None), 200

    @app.route("/event", methods=["GET"])
    def event_check():
        result = check_events()
        if result:
            return jsonify(result)
        return jsonify(None), 200

    @app.route("/mood", methods=["GET"])
    def mood():
        karakter = request.args.get("karakter", "shiro").strip().lower()
        if karakter not in ("shiro", "sishin"):
            karakter = "shiro"
        return jsonify(get_mood(karakter))

    @app.route("/tts", methods=["POST"])
    def tts():
        data = request.get_json(silent=True) or {}
        teks = (data.get("text") or "").strip()
        karakter = (data.get("karakter") or "shiro").strip().lower()
        if not teks:
            return jsonify({"error": "Teks kosong"}), 400

        file_path = generate_speech(teks, karakter)
        if file_path and os.path.exists(file_path):
            mimetype = "audio/mpeg" if file_path.endswith(".mp3") else "audio/wav"
            response = send_file(file_path, mimetype=mimetype, as_attachment=False)
            @response.call_on_close
            def cleanup():
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            return response
        return jsonify({"error": "Gagal generate suara"}), 500

    @app.route("/upload", methods=["POST"])
    def upload_image():
        try:
            if "image" not in request.files:
                return jsonify({"error": "Tidak ada gambar"}), 400
            file = request.files["image"]
            if not file.filename:
                return jsonify({"error": "Nama file kosong"}), 400
            mime = file.mimetype or ""
            if mime not in ALLOWED_IMAGE_TYPES:
                return jsonify({"error": "Format gambar tidak didukung"}), 400
            image_bytes = file.read()
            if len(image_bytes) > config.MAX_UPLOAD_BYTES:
                return jsonify({"error": "Gambar terlalu besar (maks 5 MB)"}), 400
            if len(image_bytes) == 0:
                return jsonify({"error": "File gambar kosong"}), 400
            caption = request.form.get("caption", "").strip()
            karakter = (request.form.get("karakter") or "shiro").strip().lower()
            deskripsi = deskripsi_gambar(image_bytes)
            if caption:
                prompt_user = f"Kakak Shin mengirim gambar. {deskripsi}. Caption: '{caption}'. Komentari dengan manis!"
            else:
                prompt_user = f"Kakak Shin mengirim gambar. {deskripsi}. Komentari dengan manis!"
            jawaban_data, status = jawab_shiro(prompt_user, preferred_karakter=karakter)
            return jsonify({
                "reply": jawaban_data.get("text", ""),
                "suara": jawaban_data.get("suara", jawaban_data.get("text", "")),
                "status": status,
                "deskripsi": deskripsi,
                "karakter": jawaban_data.get("karakter", karakter),
            })
        except Exception as exc:
            logger.exception("Upload failed: %s", exc)
            return jsonify({"error": "Gagal memproses gambar"}), 500

    @app.route("/voice", methods=["POST"])
    def voice():
        # (Tidak diubah) – masih menerima teks dari frontend
        if request.is_json:
            data = request.get_json(silent=True) or {}
            text = (data.get("text") or "").strip()
            karakter = (data.get("karakter") or "shiro").strip().lower()
        else:
            text = (request.form.get("text") or "").strip()
            karakter = (request.form.get("karakter") or "shiro").strip().lower()
        if not text:
            return jsonify({"error": "Teks suara kosong"}), 400
        jawaban_data, status = jawab_shiro(text, preferred_karakter=karakter)
        return jsonify({
            "text": text,
            "reply": jawaban_data.get("text", ""),
            "suara": jawaban_data.get("suara", ""),
            "status": status,
            "karakter": jawaban_data.get("karakter", karakter),
        })

    @app.route("/sawer", methods=["POST"])
    def sawer():
        data = request.get_json(silent=True) or {}
        try:
            amount = int(data.get("amount", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Nominal tidak valid"}), 400
        if amount < 100:
            return jsonify({"error": "Nominal minimal 100"}), 400
        karakter = (data.get("karakter") or "shiro").strip().lower()
        result = apply_sawer(amount, karakter)
        return jsonify(result)

    @app.route("/cleanup", methods=["POST"])
    def manual_cleanup():
        if not config.FLASK_DEBUG:
            return jsonify({"error": "Hanya tersedia dalam mode debug"}), 403
        cleanup_old_tts_files()
        return jsonify({"message": "Cleanup TTS files berhasil"}), 200

    @app.route("/about")
    def about():
        return render_template("about.html")

    # ============================================================
    # 🆕 TAMBAHAN: ENDPOINT CUACA (PROXY) – Menghindari CORS & Timeout
    # ============================================================
    @app.route("/api/weather", methods=["GET"])
    def api_weather():
        """Proxy untuk mengambil data cuaca dari Open-Meteo (server side)"""
        lat = request.args.get("lat", "-6.2088")    # default Jakarta
        lon = request.args.get("lon", "106.8456")
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&current_weather=true&timezone=Asia/Jakarta"
            )
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return jsonify(response.json())
            else:
                logger.warning(f"Open-Meteo returned status {response.status_code}")
                return jsonify({"error": "Gagal mengambil data cuaca"}), 500
        except requests.exceptions.Timeout:
            logger.error("Weather API timeout")
            return jsonify({"error": "Timeout"}), 504
        except Exception as e:
            logger.exception("Weather API error: %s", e)
            return jsonify({"error": str(e)}), 500