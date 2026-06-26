import sqlite3

from app.config import DB_PATH


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def close_db(exc=None):
    """Kept for Flask teardown compatibility."""
    pass


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
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


def muat_memori(user_id=1, limit=30):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM memori WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def simpan_memori(user, shiro, karakter="shiro", user_id=1):
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


def muat_status(user_id=1):
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


def simpan_status(status, user_id=1):
    with _connect() as conn:
        conn.execute(
            """
            UPDATE status SET affection = ?, level = ?, interaksi = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (status["affection"], status["level"], status["interaksi"], user_id),
        )
        conn.commit()


def muat_fakta(user_id=1, limit=10):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT fakta FROM fakta WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [row["fakta"] for row in rows]


def simpan_fakta(user_id, fakta):
    with _connect() as conn:
        conn.execute("INSERT INTO fakta (user_id, fakta) VALUES (?, ?)", (user_id, fakta))
        conn.commit()
