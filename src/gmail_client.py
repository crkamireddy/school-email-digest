"""Gmail integration. Fetches emails carrying the configured label,
received since a given cutoff.

Authentication is shared with Drive access — see google_auth.py for
setup. This file is correct-by-construction against the standard Gmail
API, but I have no Gmail credentials to test it against live — the
first real run is the actual test. Read it before trusting it, same as
anything else generated for you.
"""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone

from googleapiclient.discovery import build

from .google_auth import get_credentials
from .models import RawEmail

log = logging.getLogger("school_email_digest")


def _is_auto_reply(headers: dict[str, str]) -> bool:
    """True for out-of-office / vacation auto-replies, e.g. the bounce
    you get emailing a teacher over winter break. RFC 3834 has
    auto-responders mark themselves with "Auto-Submitted: auto-replied"
    (Gmail's vacation responder and Outlook both do).

    Deliberately ONLY "auto-replied", never "auto-generated": bulk
    senders like newsletter tools can use auto-generated on real school
    announcements, and dropping those silently would be far worse than
    letting an odd auto-reply through. The model prompt backs this up
    for auto-replies whose server leaves the header off.

    Header names are case-insensitive in email, and the value can carry
    parameters after a semicolon ("auto-replied; owner-email=...")."""
    for name, value in headers.items():
        if name.lower() == "auto-submitted":
            return value.split(";")[0].strip().lower() == "auto-replied"
    return False


def _decode_body(payload: dict) -> str:
    """Gmail messages are nested multipart MIME; walk to the first
    text/plain part. Falls back to text/html stripped of tags if no
    plain-text part exists."""
    def find_part(part: dict, mime_type: str) -> dict | None:
        if part.get("mimeType") == mime_type and "data" in part.get("body", {}):
            return part
        for sub in part.get("parts", []) or []:
            found = find_part(sub, mime_type)
            if found:
                return found
        return None

    part = find_part(payload, "text/plain")
    if part is None:
        part = find_part(payload, "text/html")
    if part is None:
        return ""

    data = part["body"]["data"]
    text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    if part.get("mimeType") == "text/html":
        import re
        text = re.sub(r"<[^>]+>", " ", text)
    return text


def fetch_labeled_emails(label: str, since: datetime) -> list[RawEmail]:
    """since must be timezone-aware (pipeline.py passes UTC)."""
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    # Unix seconds, not a YYYY/MM/DD date: Gmail reads a date as
    # midnight in the account's own time zone, while the cursor is UTC.
    # After an evening Pacific run the UTC date has already rolled over,
    # so a date query would start at the NEXT Pacific midnight and
    # silently skip anything arriving in between. A timestamp is one
    # exact moment with no time zone to misread.
    query = f"label:{label} after:{int(since.timestamp())}"

    results = service.users().messages().list(userId="me", q=query).execute()
    message_stubs = results.get("messages", [])

    emails: list[RawEmail] = []
    for stub in message_stubs:
        msg = service.users().messages().get(
            userId="me", id=stub["id"], format="full"
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        if _is_auto_reply(headers):
            # Opaque ID, not subject — safe in a public Actions log.
            log.info("Skipped auto-reply: message %s", msg["id"])
            continue
        body = _decode_body(msg["payload"])
        epoch_seconds = int(msg["internalDate"]) / 1000

        # Belt and braces: re-check the exact arrival time against the
        # cursor in case Gmail's after: rounds at all. Both sides UTC.
        if datetime.fromtimestamp(epoch_seconds, tz=timezone.utc) <= since:
            continue
        # The "Received:" time shown to the model stays in this machine's
        # local time, unchanged from before — only the cursor comparison
        # above needed fixing.
        internal_date = datetime.fromtimestamp(epoch_seconds)

        emails.append(
            RawEmail(
                message_id=msg["id"],
                subject=headers.get("Subject", "(no subject)"),
                sender=headers.get("From", "(unknown sender)"),
                body_text=body,
                received_at=internal_date.isoformat(),
            )
        )
    return emails
