from src.gmail_client import _is_auto_reply


def test_out_of_office_reply_is_detected():
    assert _is_auto_reply({"From": "teacher@example-elementary.org",
                           "Auto-Submitted": "auto-replied"})


def test_header_name_and_value_are_case_insensitive():
    assert _is_auto_reply({"auto-submitted": "Auto-Replied"})


def test_value_with_parameters_is_detected():
    assert _is_auto_reply({"Auto-Submitted": "auto-replied; owner-email=\"t@example.org\""})


def test_auto_generated_newsletter_is_not_skipped():
    """Bulk newsletter tools may mark real announcements auto-generated —
    those must still reach the digest."""
    assert not _is_auto_reply({"Auto-Submitted": "auto-generated"})


def test_explicit_no_and_missing_header_are_not_skipped():
    assert not _is_auto_reply({"Auto-Submitted": "no"})
    assert not _is_auto_reply({"From": "office@example-preschool.org"})


# --- fetch_labeled_emails: cursor handling (Gmail mocked, no network) ---

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.gmail_client import fetch_labeled_emails


def _fake_gmail(arrival_times: list[datetime]) -> MagicMock:
    """A stand-in Gmail service returning one plain-text message per
    arrival time, so only the cursor logic is under test."""
    service = MagicMock()
    messages = service.users.return_value.messages.return_value
    messages.list.return_value.execute.return_value = {
        "messages": [{"id": f"m{i}"} for i in range(len(arrival_times))]
    }
    messages.get.return_value.execute.side_effect = [
        {
            "id": f"m{i}",
            "internalDate": str(int(t.timestamp() * 1000)),
            "payload": {
                "headers": [{"name": "Subject", "value": f"email {i}"}],
                "mimeType": "text/plain",
                "body": {"data": "aGk="},  # "hi"
            },
        }
        for i, t in enumerate(arrival_times)
    ]
    return service


def _fetch(service, since):
    with patch("src.gmail_client.get_credentials"), \
         patch("src.gmail_client.build", return_value=service):
        return fetch_labeled_emails("School", since)


def test_query_uses_exact_unix_timestamp_not_a_date():
    # 02:18 UTC Oct 5 = 7:18pm Pacific Oct 4: the case where a
    # "after:2026/10/05" date query would have started 5 hours late.
    since = datetime(2026, 10, 5, 2, 18, tzinfo=timezone.utc)
    service = _fake_gmail([])
    _fetch(service, since)
    query = service.users.return_value.messages.return_value.list.call_args.kwargs["q"]
    assert query == f"label:School after:{int(since.timestamp())}"


def test_evening_email_after_cursor_is_kept_and_older_ones_dropped():
    since = datetime(2026, 10, 5, 2, 18, tzinfo=timezone.utc)
    evening = datetime(2026, 10, 5, 4, 0, tzinfo=timezone.utc)   # 9pm Pacific
    at_cursor = since
    before = datetime(2026, 10, 4, 23, 0, tzinfo=timezone.utc)
    emails = _fetch(_fake_gmail([evening, at_cursor, before]), since)
    assert [e.subject for e in emails] == ["email 0"]
