"""
Simple SQLite persistence for AgroChat conversations and users.

This minimal layer uses the stdlib `sqlite3` and stores conversation
messages as JSON text. It's intentionally small so it requires no
additional dependencies and is easy to extend.
"""
import os
import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

DB_DIR = Path(__file__).parent / 'data'
DB_PATH = DB_DIR / 'agrochat.db'

def init_db(path: Optional[str] = None):
    """Initialize the SQLite database and create tables if missing."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    db_file = DB_PATH if path is None else Path(path)
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            title TEXT,
            messages TEXT,
            created_at REAL,
            last_message REAL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS weather (
            location_key TEXT PRIMARY KEY,
            location_display TEXT,
            lat REAL,
            lon REAL,
            data TEXT,
            updated_at REAL
        )
        """
    )
    conn.commit()
    conn.close()

def _connect():
    return sqlite3.connect(str(DB_PATH))

def upsert_conversation(conv: Dict[str, Any]):
    """Insert or update a conversation record.

    conv must be a dict containing at least `id` and `messages` (list).
    """
    conn = _connect()
    cur = conn.cursor()
    msgs = json.dumps(conv.get('messages', []), ensure_ascii=False)
    cur.execute(
        "REPLACE INTO conversations (id, title, messages, created_at, last_message) VALUES (?, ?, ?, ?, ?)",
        (conv.get('id'), conv.get('title'), msgs, conv.get('createdAt') or conv.get('created_at') or 0, conv.get('lastMessage') or conv.get('last_message') or 0)
    )
    conn.commit()
    conn.close()

def get_all_conversations() -> List[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, title, messages, created_at, last_message FROM conversations ORDER BY last_message DESC")
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        try:
            msgs = json.loads(r[2]) if r[2] else []
        except Exception:
            msgs = []
        out.append({
            'id': r[0],
            'title': r[1],
            'messages': msgs,
            'createdAt': r[3],
            'lastMessage': r[4]
        })
    return out

def get_conversation(conv_id: str) -> Optional[Dict[str, Any]]:
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT id, title, messages, created_at, last_message FROM conversations WHERE id = ?", (conv_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    try:
        msgs = json.loads(row[2]) if row[2] else []
    except Exception:
        msgs = []
    return {
        'id': row[0],
        'title': row[1],
        'messages': msgs,
        'createdAt': row[3],
        'lastMessage': row[4]
    }

def delete_conversation(conv_id: str) -> bool:
    """Delete a conversation by ID. Returns True if deleted, False if not found."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def _normalize_location_key(location: str) -> str:
    if not location:
        return ""
    return " ".join(location.strip().lower().split())


def upsert_weather(location: str, location_display: str, lat: float, lon: float, data: Dict[str, Any]):
    """Insert or update weather JSON for a normalized location key."""
    conn = _connect()
    cur = conn.cursor()
    key = _normalize_location_key(location)
    payload = json.dumps(data, ensure_ascii=False)
    now = float(__import__('time').time())
    cur.execute(
        "REPLACE INTO weather (location_key, location_display, lat, lon, data, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (key, location_display, lat, lon, payload, now)
    )
    conn.commit()
    conn.close()


def get_weather(location: str) -> Optional[Dict[str, Any]]:
    """Return stored weather dict for a normalized location key, or None."""
    key = _normalize_location_key(location)
    if not key:
        return None
    conn = _connect()
    cur = conn.cursor()
    cur.execute("SELECT location_display, lat, lon, data, updated_at FROM weather WHERE location_key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    try:
        data = json.loads(row[3]) if row[3] else None
    except Exception:
        data = None
    return {
        'location_key': key,
        'location_display': row[0],
        'lat': row[1],
        'lon': row[2],
        'data': data,
        'updated_at': row[4]
    }
