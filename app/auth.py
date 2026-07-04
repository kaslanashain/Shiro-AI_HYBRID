"""Authentication: register, login, session helpers."""
import logging
import re
import sqlite3

from flask import session
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import _connect, _resolve_user_id, init_db

logger = logging.getLogger(__name__)

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,24}$")


def init_auth_tables():
    init_db()
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS auth_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )
        conn.commit()


def register_user(username: str, password: str, display_name: str = ""):
    username = (username or "").strip().lower()
    password = password or ""
    display_name = (display_name or username or "Tamu").strip()[:40]

    if not USERNAME_RE.match(username):
        return None, "Username 3-24 karakter (huruf, angka, underscore)"
    if len(password) < 6:
        return None, "Password minimal 6 karakter"

    init_auth_tables()
    try:
        with _connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM auth_accounts WHERE username = ?", (username,)
            ).fetchone()
            if existing:
                return None, "Username sudah dipakai"

            cur = conn.execute(
                "INSERT INTO users (nama) VALUES (?)", (display_name,)
            )
            user_id = cur.lastrowid
            conn.execute(
                """
                INSERT INTO status (user_id, affection, level, interaksi)
                VALUES (?, 50, 1, 0)
                """,
                (user_id,),
            )
            conn.execute(
                """
                INSERT INTO preferences (user_id, panggilan, topik)
                VALUES (?, ?, '')
                """,
                (user_id, display_name),
            )
            conn.execute(
                """
                INSERT INTO auth_accounts (username, password_hash, display_name, user_id)
                VALUES (?, ?, ?, ?)
                """,
                (username, generate_password_hash(password), display_name, user_id),
            )
            conn.commit()
        return user_id, None
    except sqlite3.Error as exc:
        logger.exception("Register failed: %s", exc)
        return None, "Gagal mendaftar"


def authenticate(username: str, password: str):
    username = (username or "").strip().lower()
    password = password or ""
    if not username or not password:
        return None, "Username dan password wajib diisi"

    init_auth_tables()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT a.user_id, a.password_hash, a.display_name, u.nama
            FROM auth_accounts a
            JOIN users u ON u.id = a.user_id
            WHERE a.username = ?
            """,
            (username,),
        ).fetchone()
        if not row or not check_password_hash(row["password_hash"], password):
            return None, "Username atau password salah"
        return {
            "user_id": row["user_id"],
            "username": username,
            "display_name": row["display_name"] or row["nama"],
        }, None


def login_user(username: str, password: str):
    user, err = authenticate(username, password)
    if err:
        return None, err
    session.clear()
    session["user_id"] = user["user_id"]
    session["username"] = user["username"]
    session["display_name"] = user["display_name"]
    session.permanent = True
    return user, None


def logout_user():
    session.clear()


def get_session_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return {
        "user_id": uid,
        "username": session.get("username", ""),
        "display_name": session.get("display_name", "User"),
    }


def get_current_user_id():
    user = get_session_user()
    if user:
        return user["user_id"]
    return _resolve_user_id(None)
