"""
utils/chat_history.py — Persistent Chat History

Architecture:
  - SQLite  : durable storage — every message written here permanently
  - Redis   : hot cache — last N messages per session for fast reads
              (falls back gracefully if Redis is unavailable)

Schema (SQLite):
  chat_messages(id, session_id, role, content, agent, doc_title,
                doc_bytes BLOB, user_level, timestamp)

Public API:
  save_message(session_id, role, content, agent, doc_title, doc_bytes, user_level)
  load_history(session_id) -> list[dict]
  clear_history(session_id)
"""

import sqlite3
import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ── SQLite ─────────────────────────────────────────────────────────────────
_DB_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "chat_history.db")
DB_PATH = os.getenv("CHAT_DB_PATH", _DB_DEFAULT)

# ── Redis ──────────────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB   = int(os.getenv("REDIS_DB", "0"))
REDIS_TTL  = int(os.getenv("REDIS_TTL", "86400"))   # 24 h
CACHE_SIZE = 50   # max messages kept in Redis per session

_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                        decode_responses=False, socket_connect_timeout=1)
        r.ping()
        _redis_client = r
        logger.info("Redis connected at %s:%s", REDIS_HOST, REDIS_PORT)
        return _redis_client
    except Exception as e:
        logger.warning("Redis unavailable (%s) — using SQLite only.", e)
        return None


def _get_conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    try:
        with _get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT    NOT NULL,
                    role       TEXT    NOT NULL,
                    content    TEXT    NOT NULL,
                    agent      TEXT    NOT NULL DEFAULT '',
                    doc_title  TEXT    NOT NULL DEFAULT '',
                    doc_bytes  BLOB,
                    user_level TEXT    NOT NULL DEFAULT 'intermediate',
                    timestamp  TEXT    NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_session ON chat_messages(session_id, id)")
            conn.commit()
    except Exception as e:
        logger.warning("chat_history DB init failed: %s", e)

_init_db()


# ── Redis key helpers ──────────────────────────────────────────────────────

def _rkey(session_id: str) -> str:
    return f"chat:{session_id}"


def _msg_to_cache(msg: dict) -> bytes:
    """Serialise message for Redis — exclude heavy doc_bytes."""
    lightweight = {k: v for k, v in msg.items() if k != "doc_bytes"}
    return json.dumps(lightweight).encode()


def _cache_to_msg(raw: bytes) -> dict:
    return json.loads(raw.decode())


# ── Public API ─────────────────────────────────────────────────────────────

def save_message(
    session_id: str,
    role: str,            # "user" | "assistant"
    content: str,
    agent: str = "",
    doc_title: str = "",
    doc_bytes: bytes | None = None,
    user_level: str = "intermediate",
) -> None:
    """Persist a message to SQLite and push to Redis cache."""
    ts = datetime.utcnow().isoformat()
    msg = {
        "session_id": session_id,
        "role": role,
        "content": content,
        "agent": agent,
        "doc_title": doc_title,
        "doc_bytes": doc_bytes,
        "user_level": user_level,
        "timestamp": ts,
    }

    # 1. SQLite (durable)
    try:
        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO chat_messages
                   (session_id, role, content, agent, doc_title, doc_bytes, user_level, timestamp)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (session_id, role, content, agent, doc_title, doc_bytes, user_level, ts)
            )
            conn.commit()
    except Exception as e:
        logger.warning("SQLite save_message failed: %s", e)

    # 2. Redis (hot cache — lightweight, no doc_bytes)
    try:
        r = _get_redis()
        if r:
            key = _rkey(session_id)
            r.rpush(key, _msg_to_cache(msg))
            r.ltrim(key, -CACHE_SIZE, -1)   # keep last CACHE_SIZE messages
            r.expire(key, REDIS_TTL)
    except Exception as e:
        logger.debug("Redis push failed: %s", e)


def load_history(session_id: str) -> list[dict]:
    """
    Load full chat history for a session.
    Tries Redis first (fast), falls back to SQLite.
    doc_bytes are NOT included in history (only available from SQLite on demand).
    """
    # 1. Try Redis cache
    try:
        r = _get_redis()
        if r:
            key = _rkey(session_id)
            raw_list = r.lrange(key, 0, -1)
            if raw_list:
                return [_cache_to_msg(raw) for raw in raw_list]
    except Exception as e:
        logger.debug("Redis load failed: %s", e)

    # 2. Fall back to SQLite
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT role, content, agent, doc_title, user_level, timestamp
                   FROM chat_messages WHERE session_id=? ORDER BY id ASC""",
                (session_id,)
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("SQLite load_history failed: %s", e)
        return []


def get_doc_bytes(session_id: str, doc_title: str) -> bytes | None:
    """Retrieve stored doc bytes for a specific message (from SQLite only)."""
    try:
        with _get_conn() as conn:
            row = conn.execute(
                """SELECT doc_bytes FROM chat_messages
                   WHERE session_id=? AND doc_title=? AND doc_bytes IS NOT NULL
                   ORDER BY id DESC LIMIT 1""",
                (session_id, doc_title)
            ).fetchone()
        if row:
            return bytes(row["doc_bytes"])
    except Exception as e:
        logger.warning("get_doc_bytes failed: %s", e)
    return None


def clear_history(session_id: str) -> None:
    """Delete all history for a session from both stores."""
    try:
        with _get_conn() as conn:
            conn.execute("DELETE FROM chat_messages WHERE session_id=?", (session_id,))
            conn.commit()
    except Exception as e:
        logger.warning("SQLite clear_history failed: %s", e)
    try:
        r = _get_redis()
        if r:
            r.delete(_rkey(session_id))
    except Exception as e:
        logger.debug("Redis clear failed: %s", e)
