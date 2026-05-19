"""
Database layer — SQLite.
Auto-creates the database and tables on first run.
No setup needed.
"""

import sqlite3
import os
from datetime import datetime
from config import DB_PATH, DB_DIR


def _connect():
    """Open a connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS microphones (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id  INTEGER NOT NULL,
                name       TEXT    NOT NULL,
                status     TEXT    DEFAULT 'idle',
                created_at TEXT    DEFAULT (datetime('now')),
                updated_at TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS detections (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                mic_id        INTEGER REFERENCES microphones(id),
                transcript    TEXT,
                result        TEXT,
                score_toxic   REAL DEFAULT 0,
                score_severe  REAL DEFAULT 0,
                score_obscene REAL DEFAULT 0,
                score_threat  REAL DEFAULT 0,
                score_insult  REAL DEFAULT 0,
                score_idhate  REAL DEFAULT 0,
                alerted       INTEGER DEFAULT 0,
                recording_path TEXT DEFAULT NULL,
                detected_at   TEXT DEFAULT (datetime('now'))
            );
        """)
    print("[DB] Database ready.")


def save_microphone(device_id: int, name: str) -> dict:
    """Save or update a microphone record. Returns the record as dict."""
    with _connect() as conn:
        existing = conn.execute(
            "SELECT * FROM microphones WHERE device_id = ?", (device_id,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE microphones SET name=?, updated_at=? WHERE id=?",
                (name, datetime.now().isoformat(), existing["id"])
            )
            row = conn.execute(
                "SELECT * FROM microphones WHERE id=?", (existing["id"],)
            ).fetchone()
        else:
            cur = conn.execute(
                "INSERT INTO microphones (device_id, name) VALUES (?, ?)",
                (device_id, name)
            )
            row = conn.execute(
                "SELECT * FROM microphones WHERE id=?", (cur.lastrowid,)
            ).fetchone()

        return dict(row)


def get_microphone(mic_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM microphones WHERE id=?", (mic_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_microphones() -> list:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM microphones ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


def save_detection(mic_id: int, transcript: str, result: str,
                   scores: dict, alerted: bool,
                   recording_path: str = None) -> int:
    """Save a detection result to the database."""
    with _connect() as conn:
        cur = conn.execute("""
            INSERT INTO detections
              (mic_id, transcript, result,
               score_toxic, score_severe, score_obscene,
               score_threat, score_insult, score_idhate, alerted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mic_id, transcript, result,
            scores.get("toxic",         0),
            scores.get("severe_toxic",  0),
            scores.get("obscene",       0),
            scores.get("threat",        0),
            scores.get("insult",        0),
            scores.get("identity_hate", 0),
            1 if alerted else 0,
        ))
        return cur.lastrowid