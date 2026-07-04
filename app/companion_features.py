"""Companion feature helpers — random check-ins, diary reactions."""
import random
from datetime import datetime

from app.chat import get_mood, jawab_shiro
from app.db import get_last_chat_time, muat_status


RANDOM_CHECKINS = {
    "shiro": {
        "happy": [
            "Sayang~ Shiro cuma mau bilang kamu keren banget hari ini!",
            "Ehehe~ Aku lagi mikirin kamu. Semoga harimu manis ya!",
            "Kakak Shin, jangan lupa istirahat sebentar ya. Shiro sayang!",
            "Hmm~ Cuacanya bagus. Cocok jalan bareng Shiro nanti!",
        ],
        "blush": [
            "Sayang... kamu kangen Shiro juga kan?",
            "Shiro lagi duduk manis nungguin chat dari kamu lho~",
            "Kalau kamu bosan, Shiro bisa temenin kok!",
        ],
        "normal": [
            "Halo Sayang, apa kabar?",
            "Shiro di sini kalau kamu butuh teman bicara.",
            "Jangan lupa minum air ya, Kakak~",
        ],
        "sad": [
            "Sayang... kamu masih di sana kan?",
            "Shiro agak sedih... mungkin kita bisa ngobrol sebentar?",
            "Kalau kamu sibuk, gapapa... tapi jangan lama-lama ya...",
        ],
    },
    "sishin": {
        "happy": [
            "Kak! Sishin lagi semangat nih! Ayo ngobrol!",
            "Hehe~ Sishin kangen banget sama Kakak!",
            "Kak Shin! Main yuk! Sishin bosan sendirian~",
            "Yay! Kakak masih online! Sishin seneng!",
        ],
        "blush": [
            "Kak... Sishin lagi mikirin kamu lho.",
            "Ehehe~ Kakak lucu deh kalau diam-diam aja.",
            "Sishin di sini kok! Chat yuk!",
        ],
        "normal": [
            "Kak, apa kabar?",
            "Sishin lagi nunggu Kakak nih~",
            "Jangan lupa makan ya, Kak!",
        ],
        "sad": [
            "Kak... jangan marah ya... Sishin khawatir...",
            "Huft... Sishin jadi quiet kalau Kakak jauh...",
            "Kak, masih inget Sishin kan?",
        ],
    },
}

DIARY_REACTIONS = {
    "shiro": {
        "happy": [
            "Wah, baca diary kamu bikin Shiro seneng banget! Tulis lagi ya Sayang~",
            "Ehehe~ Shiro suka banget catatan hari ini. Kamu hebat!",
            "Diary kamu manis... Shiro simpan di hati ya.",
        ],
        "blush": [
            "Sayang... tulisanmu bikin Shiro malu-malu senang~",
            "Shiro baca diary kamu sambil senyum-senyum sendiri lho.",
            "Kalau setiap hari kamu tulis gini, Shiro makin sayang.",
        ],
        "normal": [
            "Terima kasih sudah menulis, Sayang. Shiro baca dengan senang hati.",
            "Catatan yang bagus. Shiro akan ingat momen ini.",
            "Hmm~ Hari ini terdengar cukup tenang. Shiro temani besok ya.",
        ],
        "sad": [
            "Sayang... kalau ada yang mengganggu, cerita ke Shiro ya...",
            "Shiro sedih bacanya... tapi Shiro di sini untuk kamu.",
            "Jangan simpan sendiri... Shiro mau peluk kamu virtual dulu.",
        ],
    },
    "sishin": {
        "happy": [
            "Wah! Diary Kakak seru banget! Sishin suka!",
            "Hehe~ Kakak hebat! Sishin bangga!",
            "Baca diary Kakak bikin Sishin ikutan semangat!",
        ],
        "blush": [
            "Kak... tulisanmu bikin Sishin malu-malu~",
            "Ehehe Sishin suka bacanya. Lagi lagi dong!",
            "Kak Shin manis deh kalau nulis gini.",
        ],
        "normal": [
            "Oke Kak, Sishin sudah baca! Hari ini cukup oke ya.",
            "Diary noted! Sishin simpan ingatan ini.",
            "Hmm~ Besok Sishin temenin Kakak lagi ya.",
        ],
        "sad": [
            "Kak... jangan sedih... Sishin di sini kok.",
            "Huft... Sishin juga ikutan sedih bacanya. Peluk virtual dulu!",
            "Kalau Kakak butuh teman, Sishin selalu ada.",
        ],
    },
}


def _mood_bucket(affection):
    if affection > 70:
        return "happy"
    if affection > 50:
        return "blush"
    if affection < 30:
        return "sad"
    return "normal"


def check_random_checkin(karakter="shiro", idle_minutes=0):
    """Return a proactive check-in message if conditions are met."""
    karakter = karakter if karakter in ("shiro", "sishin") else "shiro"
    status = muat_status()
    affection = status.get("affection", 50)

    last_chat = get_last_chat_time()
    if last_chat:
        diff_min = (datetime.now() - last_chat).total_seconds() / 60
    else:
        diff_min = 999

    idle_min = max(float(idle_minutes or 0), diff_min)
    mood = _mood_bucket(affection)

    # More idle = higher chance; low affection still allows gentle check-ins
    if idle_min < 2:
        return None

    chance = 0.12
    if idle_min >= 5:
        chance = 0.35
    if idle_min >= 10:
        chance = 0.5
    if affection > 60:
        chance += 0.08
    if affection < 40:
        chance += 0.05

    if random.random() > chance:
        return None

    pool = RANDOM_CHECKINS.get(karakter, RANDOM_CHECKINS["shiro"]).get(mood, [])
    if not pool:
        pool = RANDOM_CHECKINS[karakter]["normal"]

    return {
        "karakter": karakter,
        "pesan": random.choice(pool),
        "mood": mood,
        "affection": affection,
        "type": "random_checkin",
    }


def diary_react(note, karakter="shiro", use_llm=False):
    """Character responds to a diary note based on current affection mood."""
    karakter = karakter if karakter in ("shiro", "sishin") else "shiro"
    note = (note or "").strip()
    if not note:
        return {"error": "Catatan kosong"}, 400

    mood_data = get_mood(karakter)
    mood = mood_data.get("mood", "normal")
    affection = mood_data.get("affection", 50)

    if use_llm:
        try:
            prompt = (
                f"Kakak menulis diary hari ini: \"{note[:500]}\". "
                f"Balas sebagai {karakter} dalam 1-2 kalimat manis. "
                f"Mood saat ini: {mood}, afeksi {affection}%."
            )
            result, status = jawab_shiro(prompt, preferred_karakter=karakter, force_preferred=True)
            return {
                "reply": result.get("text", ""),
                "karakter": karakter,
                "mood": mood,
                "affection": affection,
                "status": status,
            }, 200
        except Exception:
            pass

    pool = DIARY_REACTIONS.get(karakter, DIARY_REACTIONS["shiro"]).get(mood, [])
    if not pool:
        pool = DIARY_REACTIONS[karakter]["normal"]

    return {
        "reply": random.choice(pool),
        "karakter": karakter,
        "mood": mood,
        "affection": affection,
    }, 200
