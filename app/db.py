import sqlite3
from datetime import datetime

from app.config import DB_PATH

GUEST_USER_ID = 1


def _resolve_user_id(user_id=None):
    """Guest = 1; logged-in user from Flask g/session."""
    if user_id is not None:
        return user_id
    try:
        from flask import g
        uid = getattr(g, "user_id", None)
        if uid:
            return uid
    except RuntimeError:
        pass
    try:
        from flask import session
        uid = session.get("user_id")
        if uid:
            return uid
    except RuntimeError:
        pass
    return GUEST_USER_ID


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def close_db(exc=None):
    """Kept for Flask teardown compatibility."""
    pass


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # ===== TABEL UTAMA =====
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT DEFAULT 'Kakak Shin',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS memori (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                karakter TEXT DEFAULT 'shiro',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS status (
                user_id INTEGER PRIMARY KEY DEFAULT 1,
                affection INTEGER DEFAULT 50,
                level INTEGER DEFAULT 1,
                interaksi INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS fakta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                fakta TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            INSERT OR IGNORE INTO users (id, nama) VALUES (1, 'Kakak Shin');
            INSERT OR IGNORE INTO status (user_id, affection, level, interaksi)
            VALUES (1, 50, 1, 0);
            """
        )

        # ===== KOLOM last_chat (tanpa default) =====
        cursor = conn.execute("PRAGMA table_info(status)")
        columns = [col[1] for col in cursor.fetchall()]
        if "last_chat" not in columns:
            conn.execute("ALTER TABLE status ADD COLUMN last_chat DATETIME")
            conn.execute("UPDATE status SET last_chat = CURRENT_TIMESTAMP WHERE last_chat IS NULL")

        # ===== TABEL preferences =====
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS preferences (
                user_id INTEGER PRIMARY KEY DEFAULT 1,
                panggilan TEXT DEFAULT 'Kakak Shin',
                topik TEXT DEFAULT '',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO preferences (user_id, panggilan, topik)
            VALUES (1, 'Kakak Shin', '')
            """
        )

        # ===== TABEL event_log (dengan trigger_date) =====
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                user_id INTEGER DEFAULT 1,
                triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                trigger_date TEXT DEFAULT (date('now'))
            );
            """
        )
        # Index unik untuk mencegah duplikasi event per hari
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_event_log_unique
            ON event_log (event_id, user_id, trigger_date);
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS story_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                karakter TEXT DEFAULT 'shiro',
                title TEXT DEFAULT 'Petualangan Baru',
                location TEXT DEFAULT 'Desa Awal',
                hp INTEGER DEFAULT 100,
                inventory TEXT DEFAULT '[]',
                scene TEXT DEFAULT '',
                history TEXT DEFAULT '[]',
                active INTEGER DEFAULT 1,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        conn.commit()


# ============================================================
# FUNGSI-FUNGSI YANG SUDAH ADA (tidak diubah)
# ============================================================

def muat_memori(user_id=None, limit=30, karakter=None):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        if karakter in ("shiro", "sishin"):
            rows = conn.execute(
                """
                SELECT role, content FROM memori
                WHERE user_id = ? AND karakter = ?
                ORDER BY timestamp DESC LIMIT ?
                """,
                (user_id, karakter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT role, content FROM memori WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def simpan_memori(user, shiro, karakter="shiro", user_id=None):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO memori (user_id, role, content, karakter) VALUES (?, ?, ?, ?)",
            (user_id, "user", user, karakter),
        )
        conn.execute(
            "INSERT INTO memori (user_id, role, content, karakter) VALUES (?, ?, ?, ?)",
            (user_id, "assistant", shiro, karakter),
        )
        conn.execute(
            """
            DELETE FROM memori
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM memori WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50
            )
            """,
            (user_id, user_id),
        )
        conn.commit()


def muat_status(user_id=None):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        row = conn.execute(
            "SELECT affection, level, interaksi FROM status WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row:
            return {
                "affection": row["affection"],
                "level": row["level"],
                "interaksi": row["interaksi"],
            }
        return {"affection": 50, "level": 1, "interaksi": 0}


def simpan_status(status, user_id=None):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        cursor = conn.execute("PRAGMA table_info(status)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'last_chat' in columns:
            conn.execute(
                """
                UPDATE status 
                SET affection = ?, level = ?, interaksi = ?, updated_at = CURRENT_TIMESTAMP, last_chat = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (status["affection"], status["level"], status["interaksi"], user_id),
            )
        else:
            conn.execute(
                """
                UPDATE status 
                SET affection = ?, level = ?, interaksi = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (status["affection"], status["level"], status["interaksi"], user_id),
            )
        conn.commit()


def muat_fakta(user_id=None, limit=10):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        rows = conn.execute(
            "SELECT fakta FROM fakta WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [row["fakta"] for row in rows]


def simpan_fakta(user_id, fakta):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        conn.execute("INSERT INTO fakta (user_id, fakta) VALUES (?, ?)", (user_id, fakta))
        conn.commit()


# ============================================================
# FUNGSI-FUNGSI BARU
# ============================================================

def get_last_chat_time(user_id=None):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        row = conn.execute("SELECT last_chat FROM status WHERE user_id = ?", (user_id,)).fetchone()
        if row and row["last_chat"]:
            return datetime.fromisoformat(row["last_chat"])
        return datetime.now()


def log_event(event_id, user_id=None):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        # Gunakan INSERT OR IGNORE dengan trigger_date agar tidak duplikat per hari
        conn.execute(
            """
            INSERT OR IGNORE INTO event_log (event_id, user_id, trigger_date)
            VALUES (?, ?, date('now'))
            """,
            (event_id, user_id),
        )
        conn.commit()


def is_event_triggered_today(event_id, user_id=None):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM event_log
            WHERE event_id = ? AND user_id = ? AND trigger_date = date('now')
            """,
            (event_id, user_id),
        ).fetchone()
        return row is not None


def muat_preferensi(user_id=None):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        row = conn.execute(
            "SELECT panggilan, topik FROM preferences WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row:
            return {"panggilan": row["panggilan"], "topik": row["topik"]}
        return {"panggilan": "Kakak Shin", "topik": ""}


def simpan_preferensi(user_id=None, panggilan=None, topik=None):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        if panggilan is not None:
            conn.execute(
                "UPDATE preferences SET panggilan = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (panggilan, user_id),
            )
        if topik is not None:
            conn.execute(
                "UPDATE preferences SET topik = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                (topik, user_id),
            )
        conn.commit()


# ============================================================
# STORY MODE
# ============================================================

def story_create(user_id=None, karakter="shiro", title="Petualangan Baru"):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        conn.execute(
            "UPDATE story_sessions SET active = 0 WHERE user_id = ? AND karakter = ?",
            (user_id, karakter),
        )
        cur = conn.execute(
            """
            INSERT INTO story_sessions (user_id, karakter, title, active)
            VALUES (?, ?, ?, 1)
            """,
            (user_id, karakter, title),
        )
        conn.commit()
        return cur.lastrowid


def story_get(session_id, user_id=None):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM story_sessions
            WHERE id = ? AND user_id = ? AND active = 1
            """,
            (session_id, user_id),
        ).fetchone()
        return dict(row) if row else None


def story_get_active(user_id=None, karakter="shiro"):
    user_id = _resolve_user_id(user_id)
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM story_sessions
            WHERE user_id = ? AND karakter = ? AND active = 1
            ORDER BY updated_at DESC LIMIT 1
            """,
            (user_id, karakter),
        ).fetchone()
        return dict(row) if row else None


def story_update(session_id, user_id=None, **fields):
    user_id = _resolve_user_id(user_id)
    allowed = {"title", "location", "hp", "inventory", "scene", "history"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    sets = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [session_id, user_id]
    with _connect() as conn:
        conn.execute(
            f"""
            UPDATE story_sessions SET {sets}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            vals,
        )
        conn.commit()
        return True