"""
Simple auth module: SQLite-backed user store with bcrypt passwords and JWT tokens.
"""

import sqlite3
import bcrypt
import jwt
import os
import json
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admissionguru.db")
SECRET_KEY = "admguru_secret_key_2025_xK9pL_Maharashtra_CET"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            email     TEXT NOT NULL UNIQUE,
            password  TEXT NOT NULL,
            phone     TEXT,
            created   TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS saved_lists (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            exam_type   TEXT,
            input_summary TEXT,
            results     TEXT,
            created     TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def register_user(name, email, password, phone=""):
    conn = get_db()
    c = conn.cursor()
    # Check if email exists
    c.execute("SELECT id FROM users WHERE email=?", (email,))
    if c.fetchone():
        conn.close()
        return None, "Email already registered"

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = datetime.datetime.utcnow().isoformat()
    c.execute(
        "INSERT INTO users (name, email, password, phone, created) VALUES (?,?,?,?,?)",
        (name, email, hashed, phone, now)
    )
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    token = _make_token(user_id, name, email)
    return {"id": user_id, "name": name, "email": email, "token": token}, None


def login_user(email, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None, "Invalid email or password"
    if not bcrypt.checkpw(password.encode("utf-8"), row["password"].encode("utf-8")):
        return None, "Invalid email or password"
    token = _make_token(row["id"], row["name"], row["email"])
    return {"id": row["id"], "name": row["name"], "email": row["email"], "token": token}, None


def _make_token(user_id, name, email):
    payload = {
        "user_id": user_id,
        "name":    name,
        "email":   email,
        "exp":     datetime.datetime.utcnow() + datetime.timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"


def save_list(user_id, exam_type, input_summary, results):
    conn = get_db()
    c = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    c.execute(
        "INSERT INTO saved_lists (user_id, exam_type, input_summary, results, created) VALUES (?,?,?,?,?)",
        (user_id, exam_type, json.dumps(input_summary), json.dumps(results), now)
    )
    conn.commit()
    list_id = c.lastrowid
    conn.close()
    return list_id


def get_saved_lists(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM saved_lists WHERE user_id=? ORDER BY created DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    result = []
    for row in rows:
        result.append({
            "id":            row["id"],
            "exam_type":     row["exam_type"],
            "input_summary": json.loads(row["input_summary"]) if row["input_summary"] else {},
            "results":       json.loads(row["results"])       if row["results"]       else [],
            "created":       row["created"],
        })
    return result


def delete_saved_list(user_id, list_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM saved_lists WHERE id=? AND user_id=?", (list_id, user_id))
    conn.commit()
    affected = c.rowcount
    conn.close()
    return affected > 0


def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, name, email, phone, created FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None
