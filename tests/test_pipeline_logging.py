"""What the run log calls each email. On GitHub Actions a public repo's
logs are public, so subjects (which can name a school) must never appear
there — only the opaque Gmail message ID. Locally, subjects are fine."""
from src.pipeline import _log_name
from tests.fixtures.sample_emails import ROOM12_FIELD_TRIP_DEADLINE as EMAIL


def test_github_actions_logs_message_id_not_subject(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    name = _log_name(EMAIL)
    assert name == "message fixture-1"
    assert EMAIL.subject not in name


def test_local_run_logs_subject(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    assert EMAIL.subject in _log_name(EMAIL)
