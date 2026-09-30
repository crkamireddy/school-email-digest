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
