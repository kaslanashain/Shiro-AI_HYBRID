import logging
import os
import requests
from flask import g, jsonify, render_template, request, send_file, session
from app import config
from app.auth import get_session_user, login_user, logout_user, register_user
from app.companion_features import check_random_checkin, diary_react
from app.chat import (
    apply_sawer, jawab_shiro,
    check_initiative, check_events, get_mood,
)
from app.vision import analyze_image, analyze_video, decode_base64_image
from app.video import VIDEO_MIMES, save_uploaded_video
from app.db import _resolve_user_id, muat_status
from app.story import get_active_story, process_story_action, start_story, STORY_THEMES
from app.tts import generate_speech, cleanup_old_tts_files
from app.voice_commands import list_available_apps, process_launch_command

logger = logging.getLogger(__name__)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = VIDEO_MIMES | {"video/mp4", "video/webm", "video/quicktime"}

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

    @app.route("/desktop")
    def desktop_pet():
        """Frameless desktop companion overlay (use with desktop_launcher.py)."""
        return render_template("desktop.html")

    @app.route("/chat", methods=["POST"])
    def chat():
        data = request.get_json(silent=True) or {}
        pesan, karakter = _chat_payload(data)
        if not pesan:
            return jsonify({"error": "Pesan kosong"}), 400

        launch = None
        voice_commands_enabled = data.get("voice_commands", True)
        if isinstance(voice_commands_enabled, str):
            voice_commands_enabled = voice_commands_enabled.lower() not in ("0", "false", "off", "no")
        else:
            voice_commands_enabled = bool(voice_commands_enabled)

        if voice_commands_enabled:
            launch = process_launch_command(pesan, karakter)
        if launch:
            return jsonify({
                "reply": launch.text,
                "suara": launch.suara,
                "status": muat_status(),
                "karakter": karakter,
                "voice_command": {
                    "ok": launch.ok,
                    "status": launch.status,
                    "app_key": launch.app_key,
                    "app_label": launch.app_label,
                },
            })

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

    @app.route("/stop-bgm")
    def stop_bgm_client():
        """Mini page: signals all open Shiro tabs (same origin) to stop BGM via localStorage."""
        return (
            "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Shiro AI</title></head>"
            "<body><script>"
            "try{localStorage.setItem('shiro_ai_stop_audio',String(Date.now()));}catch(e){}"
            "setTimeout(function(){try{window.close();}catch(e){}},400);"
            "</script></body></html>"
        )

    @app.route("/initiative", methods=["GET"])
    def initiative():
        try:
            karakter = request.args.get("karakter", "").strip().lower()
            if karakter not in ("shiro", "sishin"):
                karakter = None
            result = check_initiative(preferred_karakter=karakter)
            if result:
                return jsonify(result)
            return jsonify({}), 200
        except Exception as e:
            logger.exception("initiative error: %s", e)
            return jsonify({}), 200

    @app.route("/event", methods=["GET"])
    def event_check():
        try:
            karakter = request.args.get("karakter", "").strip().lower()
            if karakter not in ("shiro", "sishin"):
                karakter = None
            result = check_events(preferred_karakter=karakter)
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

    @app.route("/api/voice/apps", methods=["GET"])
    def voice_apps_list():
        """List whitelisted apps and whether they appear installed on this PC."""
        return jsonify({"apps": list_available_apps(), "platform": os.name})

    @app.route("/api/voice/launch", methods=["POST"])
    def voice_launch():
        """Manual launch endpoint (text command -> app open + character reply)."""
        data = request.get_json(silent=True) or {}
        text = (data.get("text") or data.get("command") or "").strip()
        karakter = (data.get("karakter") or "shiro").strip().lower()
        if karakter not in ("shiro", "sishin"):
            karakter = "shiro"
        if not text:
            return jsonify({"error": "Perintah kosong"}), 400

        launch = process_launch_command(text, karakter)
        if not launch:
            return jsonify({
                "error": "Bukan perintah buka aplikasi",
                "hint": 'Contoh: "buka chrome", "open notepad"',
            }), 400

        return jsonify({
            "ok": launch.ok,
            "status": launch.status,
            "app_key": launch.app_key,
            "app_label": launch.app_label,
            "reply": launch.text,
            "suara": launch.suara,
            "karakter": karakter,
        })

    @app.route("/api/wardrobe/catalog", methods=["GET"])
    def wardrobe_catalog():
        """Static outfit catalog for frontend asset manager."""
        static_root = os.path.join(app.root_path, "static", "live2d")

        def custom_live2d_outfit(char, label):
            custom_dir = os.path.join(static_root, "custom", char)
            if not os.path.isdir(custom_dir):
                return None
            preferred = "Sishin_l2d.model3.json" if char == "sishin" else "Shiro_l2d.model3.json"
            candidates = [preferred]
            for name in sorted(os.listdir(custom_dir)):
                if name.endswith(".model3.json") and name not in candidates:
                    candidates.append(name)
            for name in candidates:
                full = os.path.join(custom_dir, name)
                if os.path.isfile(full):
                    preview = "/static/images/sishin.png" if char == "sishin" else "/static/images/shiro.png"
                    return {
                        "id": "live2d_custom",
                        "label": label,
                        "mode": "live2d",
                        "preview": preview,
                        "modelPath": f"/static/live2d/custom/{char}/{name}",
                    }
            return None

        shiro_outfits = [
            {
                "id": "expressions",
                "label": "Ekspresi PNG (Default)",
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
                "id": "live2d_haru",
                "label": "Haru (Live2D)",
                "mode": "live2d",
                "preview": "/static/images/shiro.png",
                "modelPath": "/static/live2d/shiro/Haru.model3.json",
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
        ]
        custom_shiro = custom_live2d_outfit("shiro", "Custom (Upload)")
        if custom_shiro:
            shiro_outfits.append(custom_shiro)

        sishin_outfits = [
            {
                "id": "expressions",
                "label": "Ekspresi PNG (Default)",
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
                "id": "live2d_hiyori",
                "label": "Hiyori (Live2D)",
                "mode": "live2d",
                "preview": "/static/images/sishin.png",
                "modelPath": "/static/live2d/samples/hiyori/Hiyori.model3.json",
            },
        ]
        custom_sishin = custom_live2d_outfit("sishin", "Custom (Upload)")
        if custom_sishin:
            sishin_outfits.append(custom_sishin)

        return jsonify({
            "outfits": {
                "shiro": shiro_outfits,
                "sishin": sishin_outfits,
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
        """Multipart image upload → multimodal vision (Shiro / Sishin)."""
        try:
            image_bytes = None
            mime = "image/jpeg"
            caption = ""
            karakter = "shiro"
            affection = 50

            if request.is_json:
                data = request.get_json(silent=True) or {}
                payload = data.get("image_base64") or data.get("image")
                if not payload:
                    return jsonify({"error": "image_base64 kosong"}), 400
                image_bytes, mime = decode_base64_image(payload)
                caption = (data.get("caption") or data.get("message") or "").strip()
                karakter = (data.get("character_name") or data.get("karakter") or "shiro").strip().lower()
                affection = data.get("affection_level", data.get("affection", 50))
            else:
                if "image" not in request.files:
                    return jsonify({"error": "Tidak ada gambar"}), 400
                file = request.files["image"]
                if not file.filename:
                    return jsonify({"error": "Nama file kosong"}), 400
                mime = file.mimetype or "image/jpeg"
                if mime not in ALLOWED_IMAGE_TYPES:
                    return jsonify({"error": "Format gambar tidak didukung"}), 400
                image_bytes = file.read()
                if len(image_bytes) > config.MAX_UPLOAD_BYTES:
                    return jsonify({"error": "Gambar terlalu besar (maks 5 MB)"}), 400
                if len(image_bytes) == 0:
                    return jsonify({"error": "File gambar kosong"}), 400
                caption = request.form.get("caption", "").strip()
                karakter = (request.form.get("karakter") or request.form.get("character_name") or "shiro").strip().lower()
                affection = request.form.get("affection_level") or request.form.get("affection") or 50

            if karakter not in ("shiro", "sishin"):
                karakter = "shiro"

            status = muat_status()
            try:
                affection = int(affection)
            except (TypeError, ValueError):
                affection = status.get("affection", 50)

            result = analyze_image(
                image_bytes,
                mime,
                character_name=karakter,
                affection_level=affection,
                user_caption=caption,
            )

            from app.db import simpan_memori
            mem_text = caption or "[foto]"
            simpan_memori(mem_text, result.get("text", ""), karakter)

            return jsonify({
                "reply": result.get("text", ""),
                "suara": result.get("suara", result.get("text", "")),
                "status": status,
                "karakter": result.get("karakter", karakter),
                "affection_level": result.get("affection_level", affection),
                "vision_ok": result.get("vision_ok", False),
                "provider": result.get("provider"),
            })
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            logger.exception("Upload failed: %s", exc)
            return jsonify({"error": "Gagal memproses gambar"}), 500

    @app.route("/upload_video", methods=["POST"])
    def upload_video():
        """Multipart video upload → keyframe extraction → Gemini Vision."""
        try:
            video_bytes = None
            mime = "video/mp4"
            caption = ""
            karakter = "shiro"
            affection = 50
            filename = ""

            if "video" not in request.files:
                return jsonify({"error": "Tidak ada video"}), 400
            file = request.files["video"]
            if not file.filename:
                return jsonify({"error": "Nama file kosong"}), 400

            filename = file.filename
            mime = (file.mimetype or "video/mp4").split(";")[0].strip().lower()
            ext = os.path.splitext(filename)[1].lower()
            if mime not in ALLOWED_VIDEO_TYPES and ext not in {".mp4", ".webm", ".mov", ".m4v"}:
                return jsonify({"error": "Format video tidak didukung (mp4, webm, mov)"}), 400

            video_bytes = file.read()
            max_bytes = getattr(config, "MAX_VIDEO_UPLOAD_BYTES", 20 * 1024 * 1024)
            if len(video_bytes) > max_bytes:
                return jsonify({"error": "Video terlalu besar (maks 20 MB)"}), 400
            if len(video_bytes) == 0:
                return jsonify({"error": "File video kosong"}), 400

            caption = request.form.get("caption", "").strip()
            karakter = (request.form.get("karakter") or request.form.get("character_name") or "shiro").strip().lower()
            affection = request.form.get("affection_level") or request.form.get("affection") or 50

            if karakter not in ("shiro", "sishin"):
                karakter = "shiro"

            status = muat_status()
            try:
                affection = int(affection)
            except (TypeError, ValueError):
                affection = status.get("affection", 50)

            video_url = save_uploaded_video(video_bytes, mime, filename)

            result = analyze_video(
                video_bytes,
                mime,
                character_name=karakter,
                affection_level=affection,
                user_caption=caption,
                filename=filename,
            )

            from app.db import simpan_memori
            mem_text = caption or "[video]"
            simpan_memori(mem_text, result.get("text", ""), karakter)

            return jsonify({
                "reply": result.get("text", ""),
                "suara": result.get("suara", result.get("text", "")),
                "status": status,
                "karakter": result.get("karakter", karakter),
                "affection_level": result.get("affection_level", affection),
                "vision_ok": result.get("vision_ok", False),
                "provider": result.get("provider"),
                "video_url": video_url,
                "frame_count": result.get("frame_count"),
            })
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            logger.exception("Video upload failed: %s", exc)
            return jsonify({"error": "Gagal memproses video"}), 500

    @app.route("/api/vision/analyze", methods=["POST"])
    def api_vision_analyze():
        """
        JSON vision endpoint.
        Body: {
          "image_base64": "data:image/jpeg;base64,...",
          "character_name": "shiro"|"sishin",
          "affection_level": 0-100,
          "caption": "optional user message"
        }
        """
        try:
            data = request.get_json(silent=True) or {}
            payload = data.get("image_base64") or data.get("image")
            if not payload:
                return jsonify({"error": "image_base64 required"}), 400

            image_bytes, mime = decode_base64_image(payload)
            karakter = (data.get("character_name") or data.get("karakter") or "shiro").strip().lower()
            if karakter not in ("shiro", "sishin"):
                karakter = "shiro"

            status = muat_status()
            affection = data.get("affection_level", data.get("affection", status.get("affection", 50)))
            caption = (data.get("caption") or data.get("message") or "").strip()

            result = analyze_image(
                image_bytes,
                mime,
                character_name=karakter,
                affection_level=affection,
                user_caption=caption,
            )

            return jsonify({
                "reply": result.get("text", ""),
                "suara": result.get("suara", ""),
                "karakter": result.get("karakter", karakter),
                "affection_level": result.get("affection_level"),
                "vision_ok": result.get("vision_ok", False),
                "provider": result.get("provider"),
                "status": status,
            })
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            logger.exception("Vision analyze failed: %s", exc)
            return jsonify({"error": "Gagal menganalisis gambar"}), 500

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

        launch = process_launch_command(text, karakter)
        if launch:
            return jsonify({
                "text": text,
                "reply": launch.text,
                "suara": launch.suara,
                "status": muat_status(),
                "karakter": karakter,
                "voice_command": {
                    "ok": launch.ok,
                    "status": launch.status,
                    "app_key": launch.app_key,
                    "app_label": launch.app_label,
                },
            })

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