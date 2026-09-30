"""The sent-log / dedup store. Deliberately just SQLite: zero external
accounts, one file, works identically for you or anyone who forks this.
This is the thing that makes "don't repeat information" a checkable fact
instead of a guess the model makes from scratch every run.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

from .models import DedupStatus

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_key TEXT NOT NULL,
    school TEXT NOT NULL,
    requests_volunteer_help INTEGER NOT NULL,
    is_promotional INTEGER NOT NULL,
    summary TEXT NOT NULL,
    message_id TEXT,
    date_sent TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sent_log_topic_key ON sent_log(topic_key);

CREATE TABLE IF NOT EXISTS run_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@contextmanager
def _connect(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)


def _tokens(topic_key: str) -> set[str]:
    return {t for t in topic_key.lower().split("-") if len(t) > 2}


def check_dedup(
    db_path: str,
    topic_key: str,
    school: str,
    lookback_days: int,
    today: date | None = None,
) -> DedupStatus:
    """Exact match first; falls back to a light token-overlap check within
    the same school, to catch the same real-world event described with a
    slightly different topic_key wording. This is a heuristic, not a
    guarantee — tune it against real cases in tests/ as they come up."""
    today = today or date.today()
    cutoff = (today - timedelta(days=lookback_days)).isoformat()

    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT topic_key, date_sent FROM sent_log "
            "WHERE school = ? AND date_sent >= ? ORDER BY date_sent DESC",
            (school, cutoff),
        ).fetchall()

    if not rows:
        return DedupStatus(already_sent=False)

    exact = next((r for r in rows if r["topic_key"] == topic_key), None)
    if exact:
        return DedupStatus(already_sent=True, last_sent_date=exact["date_sent"])

    new_tokens = _tokens(topic_key)
    for r in rows:
        overlap = new_tokens & _tokens(r["topic_key"])
        if len(overlap) >= 2:
            return DedupStatus(already_sent=True, last_sent_date=r["date_sent"])

    return DedupStatus(already_sent=False)


def get_last_run(db_path: str) -> str | None:
    with _connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT value FROM run_state WHERE key = 'last_run'"
        ).fetchone()
    return row["value"] if row else None


def set_last_run(db_path: str, when_iso: str) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO run_state (key, value) VALUES ('last_run', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (when_iso,),
        )


def log_sent(
    db_path: str,
    topic_key: str,
    school: str,
    requests_volunteer_help: bool,
    is_promotional: bool,
    summary: str,
    message_id: str | None = None,
    today: date | None = None,
) -> None:
    today = today or date.today()
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO sent_log (topic_key, school, requests_volunteer_help, "
            "is_promotional, summary, message_id, date_sent) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (topic_key, school, requests_volunteer_help, is_promotional,
             summary, message_id, today.isoformat()),
        )
