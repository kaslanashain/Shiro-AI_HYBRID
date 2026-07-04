import logging
import os
import requests
from flask import g, jsonify, render_template, request, send_file, session
from app import config
from app.auth import get_session_user, login_user, logout_user, register_user
from app.companion_features import check_random_checkin, diary_react
from app.chat import (
    apply_sawer, deskripsi_gambar, jawab_shiro,
    check_initiative, check_events, get_mood,
)
from app.db import _resolve_user_id, muat_status
from app.story import get_active_story, process_story_action, start_story, STORY_THEMES
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

    @app.before_request
    def load_user_context():
        user = get_session_user()
        g.user_id = user["user_id"] if user else _resolve_user_id(None)
        g.user_display = user["display_name"] if user else "Kakak Shin"

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/chat", methods=["POST"])
    def chat():
        data = request.get_json(silent=True) or {}
        pesan, karakter = _chat_payload(data)
        if not pesan:
            return jsonify({"error": "Pesan kosong"}), 400
        jawaban_data, status = jawab_shiro(pesan, preferred_karakter=karakter, force_preferred=True)
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
        try:
            result = check_initiative()
            if result:
                return jsonify(result)
            return jsonify({}), 200
        except Exception as e:
            logger.exception("initiative error: %s", e)
            return jsonify({}), 200

    @app.route("/event", methods=["GET"])
    def event_check():
        try:
            result = check_events()
            if result:
                return jsonify(result)
            return jsonify({}), 200
        except Exception as e:
            logger.exception("event error: %s", e)
            return jsonify({}), 200

    @app.route("/mood", methods=["GET"])
    def mood():
        karakter = request.args.get("karakter", "shiro").strip().lower()
        if karakter not in ("shiro", "sishin"):
            karakter = "shiro"
        return jsonify(get_mood(karakter))

    @app.route("/api/random-checkin", methods=["GET"])
    def random_checkin():
        try:
            karakter = request.args.get("karakter", "shiro").strip().lower()
            if karakter not in ("shiro", "sishin"):
                karakter = "shiro"
            idle_minutes = request.args.get("idle_minutes", 0, type=float)
            result = check_random_checkin(karakter=karakter, idle_minutes=idle_minutes)
            if result:
                return jsonify(result)
            return jsonify({}), 200
        except Exception as e:
            logger.exception("random-checkin error: %s", e)
            return jsonify({}), 200

    @app.route("/api/diary/react", methods=["POST"])
    def diary_react_route():
        try:
            data = request.get_json(silent=True) or {}
            note = (data.get("note") or "").strip()
            karakter = (data.get("karakter") or "shiro").strip().lower()
            use_llm = bool(data.get("use_llm", False))
            payload, code = diary_react(note, karakter=karakter, use_llm=use_llm)
            return jsonify(payload), code
        except Exception as e:
            logger.exception("diary react error: %s", e)
            return jsonify({"error": "Gagal memproses diary"}), 500

    @app.route("/api/wardrobe/catalog", methods=["GET"])
    def wardrobe_catalog():
        """Static outfit catalog for frontend asset manager."""
        return jsonify({
            "outfits": {
                "shiro": [
                    {
                        "id": "live2d",
                        "label": "Live2D VTuber",
                        "mode": "live2d",
                        "preview": "/static/images/shiro.png",
                        "modelPath": "/static/live2d/shiro/shiro.model3.json",
                    },
                    {
                        "id": "expressions",
                        "label": "Ekspresi (Default)",
                        "mode": "png",
                        "preview": "/static/images/expressions/shiro_happy.png",
                        "folder": "expressions",
                        "files": {
                            "happy": "shiro_happy.png",
                            "sad": "shiro_sad.png",
                            "blush": "shiro_blush.png",
                            "fallback": "shiro.png",
                        },
                    },
                    {
                        "id": "classic",
                        "label": "Klasik",
                        "mode": "png",
                        "preview": "/static/images/shiro.png",
                        "folder": "root",
                        "files": {
                            "happy": "shiro.png",
                            "sad": "shiro.png",
                            "blush": "expressions/shiro_blush.png",
                            "fallback": "shiro.png",
                        },
                    },
                ],
                "sishin": [
                    {
                        "id": "live2d",
                        "label": "Live2D VTuber",
                        "mode": "live2d",
                        "preview": "/static/images/sishin.png",
                        "modelPath": "/static/live2d/sishin/sishin.model3.json",
                    },
                    {
                        "id": "expressions",
                        "label": "Ekspresi (Default)",
                        "mode": "png",
                        "preview": "/static/images/expressions/sishin_normal.png",
                        "folder": "expressions",
                        "files": {
                            "happy": "sishin_normal.png",
                            "sad": "sishin_sad.png",
                            "blush": "sishin_blush.png",
                            "fallback": "sishin.png",
                        },
                    },
                    {
                        "id": "classic",
                        "label": "Klasik",
                        "mode": "png",
                        "preview": "/static/images/sishin.png",
                        "folder": "root",
                        "files": {
                            "happy": "sishin.png",
                            "sad": "sishin.png",
                            "blush": "expressions/sishin_blush.png",
                            "fallback": "sishin.png",
                        },
                    },
                ],
            }
        })

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
            jawaban_data, status = jawab_shiro(prompt_user, preferred_karakter=karakter, force_preferred=True)
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
        jawaban_data, status = jawab_shiro(text, preferred_karakter=karakter, force_preferred=True)
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
    # AUTH — multi-user
    # ============================================================
    @app.route("/api/auth/register", methods=["POST"])
    def auth_register():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        display_name = (data.get("display_name") or username).strip()
        user_id, err = register_user(username, password, display_name)
        if err:
            return jsonify({"error": err}), 400
        login_user(username, password)
        return jsonify({
            "message": "Registrasi berhasil",
            "user": get_session_user(),
        })

    @app.route("/api/auth/login", methods=["POST"])
    def auth_login():
        data = request.get_json(silent=True) or {}
        user, err = login_user(
            (data.get("username") or "").strip(),
            data.get("password") or "",
        )
        if err:
            return jsonify({"error": err}), 401
        return jsonify({"message": "Login berhasil", "user": user})

    @app.route("/api/auth/logout", methods=["POST"])
    def auth_logout():
        logout_user()
        return jsonify({"message": "Logout berhasil"})

    @app.route("/api/auth/me", methods=["GET"])
    def auth_me():
        user = get_session_user()
        if not user:
            return jsonify({"guest": True, "display_name": "Kakak Shin"})
        return jsonify({"guest": False, **user})

    # ============================================================
    # STORY MODE — Dungeon Master
    # ============================================================
    @app.route("/api/story/themes", methods=["GET"])
    def story_themes():
        return jsonify({"themes": list(STORY_THEMES.keys()), "labels": STORY_THEMES})

    @app.route("/api/story/start", methods=["POST"])
    def story_start():
        data = request.get_json(silent=True) or {}
        karakter = (data.get("karakter") or "shiro").strip().lower()
        if karakter not in ("shiro", "sishin"):
            karakter = "shiro"
        theme = (data.get("theme") or "fantasy").strip().lower()
        title = (data.get("title") or "").strip() or None
        try:
            result = start_story(karakter=karakter, theme=theme, title=title)
            if result.get("error"):
                return jsonify(result), 500
            return jsonify(result)
        except Exception as exc:
            logger.exception("Story start failed: %s", exc)
            return jsonify({"error": "Gagal memulai story"}), 500

    @app.route("/api/story/action", methods=["POST"])
    def story_action():
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")
        action = (data.get("action") or "").strip()
        if not session_id or not action:
            return jsonify({"error": "session_id dan action wajib"}), 400
        try:
            result = process_story_action(int(session_id), action)
            if result.get("error"):
                return jsonify(result), 404
            return jsonify(result)
        except Exception as exc:
            logger.exception("Story action failed: %s", exc)
            return jsonify({"error": "Gagal memproses aksi"}), 500

    @app.route("/api/story/active", methods=["GET"])
    def story_active():
        karakter = request.args.get("karakter", "shiro").strip().lower()
        result = get_active_story(karakter=karakter)
        return jsonify(result or {})

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