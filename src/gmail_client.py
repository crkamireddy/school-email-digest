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
from datetime import datetime

from googleapiclient.discovery import build

from .google_auth import get_credentials
from .models import RawEmail


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
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    since_str = since.strftime("%Y/%m/%d")
    query = f"label:{label} after:{since_str}"

    results = service.users().messages().list(userId="me", q=query).execute()
    message_stubs = results.get("messages", [])

    emails: list[RawEmail] = []
    for stub in message_stubs:
        msg = service.users().messages().get(
            userId="me", id=stub["id"], format="full"
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        body = _decode_body(msg["payload"])
        internal_date = datetime.fromtimestamp(int(msg["internalDate"]) / 1000)

        # after: is day-granularity in Gmail's search syntax, so re-check
        # the actual timestamp here to avoid re-processing the whole day.
        if internal_date <= since:
            continue

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
