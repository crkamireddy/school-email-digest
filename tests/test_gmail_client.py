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
from typing import Optional
from unittest.mock import MagicMock, patch

from src.gmail_client import fetch_labeled_emails


def _fake_gmail(arrival_times: list[datetime], thread_messages: Optional[list] = None) -> MagicMock:
    """A stand-in Gmail service returning one plain-text message per
    arrival time, so only the cursor logic is under test. thread_messages
    is what every thread lookup returns (default: no sent messages)."""
    service = MagicMock()
    service.users.return_value.threads.return_value.get.return_value.execute.return_value = {
        "messages": thread_messages or []
    }
    messages = service.users.return_value.messages.return_value
    messages.list.return_value.execute.return_value = {
        "messages": [{"id": f"m{i}"} for i in range(len(arrival_times))]
    }
    messages.get.return_value.execute.side_effect = [
        {
            "id": f"m{i}",
            "threadId": f"t{i}",
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


def _ms(t: datetime) -> str:
    return str(int(t.timestamp() * 1000))


def test_staff_reply_in_a_thread_the_family_started_is_flagged_not_skipped():
    """Lost-lunchbox / meeting-time case: the family asked, staff answered.
    Kept and flagged — the model decides whether it carries an action."""
    since = datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc)
    asked = datetime(2026, 10, 8, 13, 32, tzinfo=timezone.utc)
    answered = datetime(2026, 10, 8, 14, 5, tzinfo=timezone.utc)
    service = _fake_gmail([answered], thread_messages=[
        {"labelIds": ["SENT"], "internalDate": _ms(asked)},
        {"labelIds": ["INBOX"], "internalDate": _ms(answered)},
    ])
    [email] = _fetch(service, since)
    assert email.family_in_thread is True


def test_broadcast_the_family_replied_to_later_is_not_flagged():
    """Only a sent message BEFORE this one counts — replying to a school
    announcement afterward doesn't change what the announcement was."""
    since = datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc)
    broadcast = datetime(2026, 10, 8, 14, 0, tzinfo=timezone.utc)
    replied = datetime(2026, 10, 8, 15, 0, tzinfo=timezone.utc)
    service = _fake_gmail([broadcast], thread_messages=[
        {"labelIds": ["INBOX"], "internalDate": _ms(broadcast)},
        {"labelIds": ["SENT"], "internalDate": _ms(replied)},
    ])
    [email] = _fetch(service, since)
    assert email.family_in_thread is False


def test_group_thread_with_no_family_messages_is_not_flagged():
    since = datetime(2026, 10, 7, 0, 0, tzinfo=timezone.utc)
    first = datetime(2026, 10, 5, 23, 0, tzinfo=timezone.utc)
    update = datetime(2026, 10, 7, 17, 57, tzinfo=timezone.utc)
    service = _fake_gmail([update], thread_messages=[
        {"labelIds": ["INBOX"], "internalDate": _ms(first)},
        {"labelIds": ["INBOX"], "internalDate": _ms(update)},
    ])
    [email] = _fetch(service, since)
    assert email.family_in_thread is False


# --- _decode_body: which MIME part the model actually gets to read ---

import base64

from src.gmail_client import _decode_body


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode()


def _alternative(plain: str, html_body: str) -> dict:
    """multipart/alternative: the same message as plain text AND HTML,
    the shape most school mailers send."""
    return {
        "mimeType": "multipart/alternative",
        "body": {},
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _b64(plain)}},
            {"mimeType": "text/html", "body": {"data": _b64(html_body)}},
        ],
    }


CLOSURE_HTML = (
    "<html><head><style>.x { color: red; }</style></head><body>"
    "<p>Dear Families,</p>"
    "<p>School is canceled tomorrow due to a power outage. "
    "Please watch your email for updates.</p>"
    "<p>Questions? Ask Dr. Example &amp; the front office.</p>"
    "</body></html>"
)


def test_placeholder_plain_part_falls_back_to_html():
    """School-closure case: the plain part was just a placeholder
    comment, so the model only ever saw the subject line."""
    text = _decode_body(_alternative("<!--placeholder-->", CLOSURE_HTML))
    assert "power outage" in text
    assert "Please watch your email for updates" in text


def test_empty_plain_part_falls_back_to_html():
    """Some mailers ship an empty plain part."""
    assert "power outage" in _decode_body(_alternative("", CLOSURE_HTML))


def test_real_plain_part_is_still_preferred():
    plain = "Field trip is tomorrow. Please pack a nut-free bag lunch and a hat."
    assert _decode_body(_alternative(plain, CLOSURE_HTML)) == plain


def test_html_conversion_drops_css_and_decodes_entities():
    text = _decode_body(_alternative("", CLOSURE_HTML))
    assert "color: red" not in text
    assert "<p>" not in text
    assert "Dr. Example & the front office" in text


def test_html_conversion_keeps_paragraphs_on_separate_lines():
    text = _decode_body(_alternative("", CLOSURE_HTML))
    assert text.splitlines()[0] == "Dear Families,"


def test_placeholder_plain_with_no_html_part_returns_what_there_is():
    payload = {"mimeType": "text/plain", "body": {"data": _b64("hi")}}
    assert _decode_body(payload) == "hi"


def test_thread_lookup_failure_does_not_fail_the_fetch():
    """A transient Gmail 500 on the thread lookup was seen in testing —
    the email must still come through, just without the thread hint."""
    since = datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc)
    service = _fake_gmail([datetime(2026, 10, 8, 14, 0, tzinfo=timezone.utc)])
    service.users.return_value.threads.return_value.get.return_value.execute.side_effect = \
        RuntimeError("backendError")
    [email] = _fetch(service, since)
    assert email.family_in_thread is False
