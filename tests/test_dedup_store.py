from datetime import date, timedelta

from src import dedup_store


def test_no_prior_sends_means_not_already_sent(tmp_path):
    db = str(tmp_path / "test.db")
    dedup_store.init_db(db)
    status = dedup_store.check_dedup(db, "fall-fundraiser-2026", "Example Elementary", lookback_days=21)
    assert status.already_sent is False


def test_exact_topic_key_match_is_caught(tmp_path):
    db = str(tmp_path / "test.db")
    dedup_store.init_db(db)
    dedup_store.log_sent(db, "fall-fundraiser-2026", "Example Elementary", False, True, "First mention")

    status = dedup_store.check_dedup(db, "fall-fundraiser-2026", "Example Elementary", lookback_days=21)
    assert status.already_sent is True
    assert status.last_sent_date == date.today().isoformat()


def test_reworded_topic_key_is_caught_by_token_overlap(tmp_path):
    """Same real-world event, different LLM-generated key wording —
    this is the exact drift problem flagged when we designed this."""
    db = str(tmp_path / "test.db")
    dedup_store.init_db(db)
    dedup_store.log_sent(db, "fall-fundraiser-2026", "Example Elementary", False, True, "First mention")

    status = dedup_store.check_dedup(db, "annual-fall-fundraiser", "Example Elementary", lookback_days=21)
    assert status.already_sent is True


def test_unrelated_topic_is_not_falsely_matched(tmp_path):
    db = str(tmp_path / "test.db")
    dedup_store.init_db(db)
    dedup_store.log_sent(db, "fall-fundraiser-2026", "Example Elementary", False, True, "First mention")

    status = dedup_store.check_dedup(db, "room12-field-trip-oct", "Example Elementary", lookback_days=21)
    assert status.already_sent is False


def test_different_school_does_not_cross_contaminate(tmp_path):
    db = str(tmp_path / "test.db")
    dedup_store.init_db(db)
    dedup_store.log_sent(db, "fall-fundraiser-2026", "Example Elementary", False, True, "First mention")

    status = dedup_store.check_dedup(
        db, "fall-fundraiser-2026", "Example Preschool", lookback_days=21
    )
    assert status.already_sent is False


def test_outside_lookback_window_is_treated_as_new(tmp_path, monkeypatch):
    db = str(tmp_path / "test.db")
    dedup_store.init_db(db)
    old_date = date.today() - timedelta(days=30)
    dedup_store.log_sent(db, "fall-fundraiser-2026", "Example Elementary", False, True, "Old mention", today=old_date)

    status = dedup_store.check_dedup(db, "fall-fundraiser-2026", "Example Elementary", lookback_days=21)
    assert status.already_sent is False


def test_last_run_roundtrip(tmp_path):
    db = str(tmp_path / "test.db")
    dedup_store.init_db(db)
    assert dedup_store.get_last_run(db) is None

    dedup_store.set_last_run(db, "2026-09-08T09:00:00")
    assert dedup_store.get_last_run(db) == "2026-09-08T09:00:00"

    dedup_store.set_last_run(db, "2026-09-08T17:00:00")
    assert dedup_store.get_last_run(db) == "2026-09-08T17:00:00"


# --- Migration from the original single-`category` layout ---------------

import sqlite3

import pytest

_OLD_LAYOUT = """
CREATE TABLE sent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_key TEXT NOT NULL,
    school TEXT NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    message_id TEXT,
    date_sent TEXT NOT NULL
);
CREATE TABLE run_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT INTO run_state VALUES ('last_run', '2026-09-30T20:34:40');
"""

_OLD_ROWS = [
    ("pta-chaperones", "volunteer_ask"),
    ("fun-run-pledges", "fundraiser"),
    ("permission-slip", "deadline"),
    ("early-dismissal", "schedule_change"),
    ("class-newsletter", "classroom_update"),
]


def _old_layout_db(tmp_path, schema=_OLD_LAYOUT):
    db = str(tmp_path / "old.db")
    conn = sqlite3.connect(db)
    conn.executescript(schema)
    today = date.today().isoformat()
    for topic_key, category in _OLD_ROWS:
        conn.execute(
            "INSERT INTO sent_log (topic_key, school, category, summary, date_sent) "
            "VALUES (?, 'Example Elementary', ?, 'x', ?)",
            (topic_key, category, today),
        )
    conn.commit()
    conn.close()
    return db


def _flags(db):
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT topic_key, requests_volunteer_help, is_promotional FROM sent_log ORDER BY id"
    ).fetchall()
    conn.close()
    return {k: (v, p) for k, v, p in rows}


def test_old_categories_become_the_matching_flags(tmp_path):
    db = _old_layout_db(tmp_path)
    dedup_store.init_db(db)
    assert _flags(db) == {
        "pta-chaperones": (1, 0),
        "fun-run-pledges": (0, 1),
        "permission-slip": (0, 0),
        "early-dismissal": (0, 0),
        "class-newsletter": (0, 0),
    }


def test_after_migration_logging_dedup_and_cursor_all_work(tmp_path):
    db = _old_layout_db(tmp_path)
    dedup_store.init_db(db)

    # The write that used to crash with "no column named requests_volunteer_help"
    dedup_store.log_sent(db, "clean-clothes-bag", "Example Elementary", False, False, "x")

    assert dedup_store.check_dedup(db, "clean-clothes-bag", "Example Elementary", 21).already_sent
    assert dedup_store.check_dedup(db, "permission-slip", "Example Elementary", 21).already_sent
    assert dedup_store.get_last_run(db) == "2026-09-30T20:34:40"


def test_migration_is_a_no_op_the_second_time(tmp_path):
    db = _old_layout_db(tmp_path)
    dedup_store.init_db(db)
    before = _flags(db)
    dedup_store.init_db(db)
    assert _flags(db) == before


def test_failed_migration_leaves_old_table_untouched(tmp_path):
    # An old table missing message_id makes the copy step fail partway
    # through the rebuild — the whole thing must roll back.
    broken = _OLD_LAYOUT.replace("    message_id TEXT,\n", "")
    db = _old_layout_db(tmp_path, schema=broken)

    with pytest.raises(sqlite3.OperationalError):
        dedup_store.init_db(db)

    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    columns = {r[1] for r in conn.execute("PRAGMA table_info(sent_log)")}
    count = conn.execute("SELECT count(*) FROM sent_log").fetchone()[0]
    conn.close()
    assert "sent_log_new" not in tables
    assert "category" in columns
    assert count == len(_OLD_ROWS)
