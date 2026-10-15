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
import html
import logging
import re
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


# Below this many visible characters, a text/plain part is treated as a
# placeholder rather than the real message. Real cases: one school bulk
# mailer ships "<!--placeholder-->" (18 chars) and a billing system
# ships an empty part — the actual content lives only in the HTML
# version. A genuinely short plain reply ("Thanks!") also
# falls under this, which is harmless: its HTML version says the same.
_MIN_PLAIN_TEXT_CHARS = 50


def _html_to_text(html_text: str) -> str:
    """Good-enough HTML → text for the model to read. Not a full HTML
    parser (no new dependency for this); the model tolerates a little
    mess but not 20KB of CSS, which is what a bare tag-strip leaves."""
    text = re.sub(r"<!--.*?-->", " ", html_text, flags=re.S)
    text = re.sub(r"<(style|script|head)\b.*?</\1\s*>", " ", text, flags=re.S | re.I)
    # Keep line structure, so a list of dates reads as a list.
    text = re.sub(r"<br\s*/?>|</(p|div|li|tr|h[1-6])\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def _has_real_text(plain_text: str) -> bool:
    visible = re.sub(r"<!--.*?-->", "", plain_text, flags=re.S)
    return len("".join(visible.split())) >= _MIN_PLAIN_TEXT_CHARS


def _decode_body(payload: dict) -> str:
    """Gmail messages are nested multipart MIME; walk to the first
    text/plain part. Uses the text/html part instead (converted to
    text) when there's no plain part, or when the plain part is empty or
    just a placeholder — otherwise the model sees only the subject line
    (how a school-closure email once lost all its details)."""
    def find_part(part: dict, mime_type: str) -> dict | None:
        if part.get("mimeType") == mime_type and "data" in part.get("body", {}):
            return part
        for sub in part.get("parts", []) or []:
            found = find_part(sub, mime_type)
            if found:
                return found
        return None

    def decode(part: dict) -> str:
        return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")

    plain_part = find_part(payload, "text/plain")
    plain_text = decode(plain_part) if plain_part else ""
    if _has_real_text(plain_text):
        return plain_text

    html_part = find_part(payload, "text/html")
    if html_part is None:
        return plain_text
    return _html_to_text(decode(html_part))


def _family_already_in_thread(service, msg: dict) -> bool:
    """True if this account sent a message earlier in the same thread —
    usually staff answering something the family asked or wrote (a lost
    bike, a meeting about their child). Passed to the model as a hint,
    not used to skip: some of those replies carry an action (a meeting
    time, a Zoom link), and Gmail can thread separate same-subject
    broadcasts together, so one reply to a weekly newsletter would
    otherwise hide every later one. Gmail's own SENT label is the fact
    used, so no email address needs configuring. Only messages BEFORE
    this one count: replying later doesn't change what this email was."""
    try:
        thread = service.users().threads().get(
            userId="me", id=msg["threadId"], format="minimal"
        ).execute()
    except Exception:
        # This runs during the fetch, before pipeline.py's per-email
        # safety net — a transient Gmail error here (a 500 was seen in
        # testing) must not fail the whole run. False is the safe side:
        # the email just gets the normal rules, no thread hint.
        log.warning("Couldn't check thread for message %s — treating as not "
                    "a family conversation", msg["id"], exc_info=True)
        return False
    arrived = int(msg["internalDate"])
    return any(
        "SENT" in m.get("labelIds", []) and int(m["internalDate"]) < arrived
        for m in thread.get("messages", [])
    )


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
                family_in_thread=_family_already_in_thread(service, msg),
            )
        )
    return emails
