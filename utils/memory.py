"""
utils/memory.py — Student Memory & Progress Tracking

Persists per-student learning history in a local SQLite database.
Every topic the student touches is recorded with the agent that handled it,
the timestamp, and the user level at the time.

Public API (used by team/interface.py and ui/app.py):
    record_topic(session_id, topic, agent, user_level)
    get_progress(session_id)       -> StudentProgress
    get_gap_analysis(session_id)   -> GapAnalysis
    clear_progress(session_id)
"""

import sqlite3
import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Database path — stored next to this file by default, overridable via env
# --------------------------------------------------------------------------
_DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "student_memory.db")
DB_PATH = os.getenv("STUDENT_DB_PATH", _DEFAULT_DB)


def _get_conn() -> sqlite3.Connection:
    """Open (and auto-create) the SQLite database."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    """Create tables if they don't exist yet."""
    try:
        with _get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS topic_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT    NOT NULL,
                    topic       TEXT    NOT NULL,
                    topic_clean TEXT    NOT NULL,
                    agent       TEXT    NOT NULL,
                    user_level  TEXT    NOT NULL DEFAULT 'intermediate',
                    timestamp   TEXT    NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session
                ON topic_history(session_id)
            """)
            conn.commit()
    except Exception as exc:
        logger.warning("Memory DB init failed (%s) — memory disabled.", exc)


_init_db()


# --------------------------------------------------------------------------
# Data classes
# --------------------------------------------------------------------------

@dataclass
class TopicRecord:
    topic: str
    topic_clean: str
    agent: str
    user_level: str
    timestamp: str


@dataclass
class StudentProgress:
    session_id: str
    total_topics: int
    topics_by_agent: dict          # agent -> list of topic strings
    unique_topics: list[str]       # deduplicated clean topic names
    recent_topics: list[TopicRecord]  # last 10 records
    level_distribution: dict       # level -> count
    first_seen: str
    last_seen: str


@dataclass
class GapAnalysis:
    """
    Compares the student's covered topics against the Prolog prerequisite graph
    to find what they should study next.
    """
    covered_topics: list[str]           # prolog atoms the student has touched
    recommended_next: list[str]         # topics whose prereqs are all covered
    missing_prerequisites: dict         # topic -> list of missing prereqs
    suggested_focus: str                # short human-readable recommendation


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _clean_topic(topic: str) -> str:
    """Lowercase, strip, collapse whitespace for deduplication."""
    return " ".join(topic.lower().strip().split())


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def record_topic(
    session_id: str,
    topic: str,
    agent: str,
    user_level: str = "intermediate",
) -> None:
    """
    Persist a topic interaction to the database.
    Safe no-op on any error.
    """
    try:
        with _get_conn() as conn:
            conn.execute(
                """
                INSERT INTO topic_history
                    (session_id, topic, topic_clean, agent, user_level, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    topic,
                    _clean_topic(topic),
                    agent,
                    user_level,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
        logger.debug("Recorded topic '%s' for session %s", topic, session_id)
    except Exception as exc:
        logger.warning("record_topic failed (%s) — skipping.", exc)


def get_progress(session_id: str) -> StudentProgress | None:
    """
    Return a StudentProgress snapshot for this session.
    Returns None if no history exists or DB is unavailable.
    """
    try:
        with _get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM topic_history WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,),
            ).fetchall()

        if not rows:
            return None

        topics_by_agent: dict = {}
        level_dist: dict = {}
        unique_clean: list = []
        seen_clean: set = set()

        for r in rows:
            agent = r["agent"]
            level = r["user_level"]
            clean = r["topic_clean"]

            topics_by_agent.setdefault(agent, []).append(r["topic"])
            level_dist[level] = level_dist.get(level, 0) + 1
            if clean not in seen_clean:
                seen_clean.add(clean)
                unique_clean.append(clean)

        recent = [
            TopicRecord(
                topic=r["topic"],
                topic_clean=r["topic_clean"],
                agent=r["agent"],
                user_level=r["user_level"],
                timestamp=r["timestamp"],
            )
            for r in rows[-10:]
        ]

        return StudentProgress(
            session_id=session_id,
            total_topics=len(rows),
            topics_by_agent=topics_by_agent,
            unique_topics=unique_clean,
            recent_topics=recent,
            level_distribution=level_dist,
            first_seen=rows[0]["timestamp"],
            last_seen=rows[-1]["timestamp"],
        )
    except Exception as exc:
        logger.warning("get_progress failed (%s).", exc)
        return None


def get_gap_analysis(session_id: str) -> GapAnalysis | None:
    """
    Use the Prolog prerequisite graph to find knowledge gaps.
    Returns None if memory or Prolog are unavailable.
    """
    try:
        from utils.prolog_engine import PROLOG_AVAILABLE, TOPIC_ALIASES, get_prerequisites

        progress = get_progress(session_id)
        if not progress:
            return GapAnalysis(
                covered_topics=[],
                recommended_next=[],
                missing_prerequisites={},
                suggested_focus="Start by exploring any topic — I'll track your progress!",
            )

        # Map student's topic strings → known Prolog atoms
        covered_atoms: set[str] = set()
        for clean_topic in progress.unique_topics:
            for atom, aliases in TOPIC_ALIASES.items():
                if any(alias in clean_topic for alias in aliases):
                    covered_atoms.add(atom)

        # All known topics in the graph
        all_atoms = set(TOPIC_ALIASES.keys())
        uncovered = all_atoms - covered_atoms

        # Find topics whose ALL prerequisites are already covered
        recommended: list[str] = []
        missing_prereqs: dict = {}

        for topic in uncovered:
            if not PROLOG_AVAILABLE:
                break
            prereqs = get_prerequisites(topic)
            missing = [p for p in prereqs if p not in covered_atoms]
            if not missing:
                recommended.append(topic)
            else:
                missing_prereqs[topic] = missing

        # Sort recommended by how many topics depend on it (proxy for importance)
        recommended.sort()

        # Suggested focus: first recommended, or simplest uncovered
        if recommended:
            focus_atom = recommended[0]
            suggested_focus = (
                f"You're ready to learn **{focus_atom.replace('_', ' ').title()}** — "
                f"all its prerequisites are covered!"
            )
        elif covered_atoms:
            suggested_focus = "Great progress! Keep exploring advanced topics."
        else:
            suggested_focus = "Start with **Algebra** or **Programming Basics** — no prerequisites needed."

        return GapAnalysis(
            covered_topics=sorted(covered_atoms),
            recommended_next=recommended[:5],  # top 5
            missing_prerequisites=missing_prereqs,
            suggested_focus=suggested_focus,
        )

    except Exception as exc:
        logger.warning("get_gap_analysis failed (%s).", exc)
        return None


def clear_progress(session_id: str) -> None:
    """Delete all history for this session. Safe no-op on error."""
    try:
        with _get_conn() as conn:
            conn.execute(
                "DELETE FROM topic_history WHERE session_id = ?",
                (session_id,),
            )
            conn.commit()
        logger.info("Cleared progress for session %s", session_id)
    except Exception as exc:
        logger.warning("clear_progress failed (%s).", exc)
