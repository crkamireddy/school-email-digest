"""Decide stage. Deliberately NOT an LLM call. Two independent facts —
does this only matter for a specific class, is this the kind of thing
that shouldn't repeat every time it's mentioned — are all inclusion
ever depends on. Everything else survives by default; there's no fixed
topic list to keep in sync with whatever a school emails about next.
Kept as a plain function specifically so it's fully unit-testable
without touching the network.
"""
from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, datetime, timedelta

from .config import Config
from .models import DedupStatus, Decision, EmailExtraction, ExtractedItem


def _within_deadline_window(deadline_date: str | None, today: date, window_days: int) -> bool:
    if not deadline_date:
        return False
    try:
        d = datetime.strptime(deadline_date, "%Y-%m-%d").date()
    except ValueError:
        return False
    return today <= d <= today + timedelta(days=window_days)


def _should_include(
    item: ExtractedItem,
    dedup_status: DedupStatus,
    config: Config,
    today: date,
) -> bool:
    """Both checks are independent and both must pass when they apply —
    an item can be a volunteer ask AND promotional at once (e.g. "help
    run the fundraiser table"), and each condition gates it separately.
    Neither flag set means: always include, same as schedule changes,
    deadlines, and routine updates always have."""
    if item.requests_volunteer_help and config.rules.volunteer_asks_only_for_relevant_classes:
        # A class actually being named, and not matching, is what makes
        # this wrong-grade-specific (the 8th grade vision screening
        # case, when this family only has a 6th grader) — that's the
        # case this gate exists for. No class named at all means this
        # is genuinely schoolwide, same as any other schoolwide content,
        # and belongs here regardless of grade — a general "join our
        # volunteer list" ask isn't excluded just for being general.
        if item.classes_mentioned and not item.relevant_classes_mentioned:
            return False

    if item.is_promotional:
        within_window = _within_deadline_window(
            item.deadline_date, today, config.rules.deadline_window_days
        )
        if not (within_window or not dedup_status.already_sent):
            return False

    return True


# Backstop for the prompt's "never copy credentials" rule: in testing
# the model once put a shared account's username and password straight
# into a summary. A credential word followed by something value-shaped
# ("password: hunter22", "the passcode is 4417"). Values must be 4+
# characters, which skips "in"/"the"/"for"; _NOT_A_SECRET skips the
# common harmless follow-ons ("password reset", "login details").
_SECRET_RE = re.compile(
    r"\b(?:password|passcode|passwd|pwd|pin|user\s?name|"
    r"(?:login|access|door|gate|entry)\s+code)s?\b"
    r"\s*(?:is|was|:|=|-)?\s*[\"'(]?([^\s\"'),.;]{4,})",
    re.IGNORECASE,
)
_NOT_A_SECRET = {
    "will", "must", "have", "should", "reset", "resets", "link", "details",
    "sent", "shared", "provided", "included", "attached", "below", "above",
    "info", "information", "change", "changes", "required", "needed", "here",
    "were", "that", "this", "from", "with", "when", "into", "only", "email",
}


def _looks_like_it_has_a_secret(text: str) -> bool:
    return any(
        m.group(1).lower() not in _NOT_A_SECRET for m in _SECRET_RE.finditer(text)
    )


def _format_deadline_date(deadline_date: str, today: date) -> str:
    """Human-readable, e.g. 'September 12' — the year only gets added
    when it's not the current year, since for typical near-term school
    dates it's just noise."""
    d = datetime.strptime(deadline_date, "%Y-%m-%d").date()
    formatted = f"{d.strftime('%B')} {d.day}"
    if d.year != today.year:
        formatted += f", {d.year}"
    return formatted


_SAME_DAY_RE = re.compile(r"\b(today|tonight|this (morning|afternoon|evening))\b", re.IGNORECASE)
_NEXT_DAY_RE = re.compile(r"\btomorrow\b", re.IGNORECASE)


def _relative_word_matches(summary: str, deadline_date: str, today: date) -> bool:
    d = datetime.strptime(deadline_date, "%Y-%m-%d").date()
    if d == today:
        return bool(_SAME_DAY_RE.search(summary))
    if d == today + timedelta(days=1):
        return bool(_NEXT_DAY_RE.search(summary))
    return False


def _format_bullet(item: ExtractedItem, today: date, is_follow_up: bool = False) -> str:
    # Repeats of the same topic still post (a follow-up about the field
    # trip often adds the detail you actually need, like "bring a bag
    # lunch"), but are tagged up front so they're easy to skim past.
    # Tag rather than hide, because topic matching is fuzzy: a wrong
    # match here costs a misleading label, not a missed email.
    prefix = "_Follow-up:_ " if is_follow_up else ""
    if not item.deadline_date:
        return f"- {prefix}{item.one_line_summary}"

    formatted_date = _format_deadline_date(item.deadline_date, today)
    # Backstop, not the primary fix: the extraction prompt is told not to
    # restate the date, but a prompt instruction is never a guarantee.
    # If it slips through anyway, don't compound it by showing the same
    # date twice — better to trust whatever the summary already says.
    if formatted_date in item.one_line_summary:
        return f"- {prefix}{item.one_line_summary}"
    # Same idea for relative words, which the prompt allows when the
    # email phrases it that way: "kickoff is today — March 3" says the
    # day twice. Only skip the date when the word is actually true right
    # now — if an email sat a day before posting, "today" is stale and
    # the real date is the only thing that tells you so.
    if _relative_word_matches(item.one_line_summary, item.deadline_date, today):
        return f"- {prefix}{item.one_line_summary}"

    return f"- {prefix}{item.one_line_summary} — {formatted_date}"


def decide(
    config: Config,
    extraction: EmailExtraction,
    dedup_statuses: dict[str, DedupStatus],
    subject: str,
    today: date | None = None,
) -> Decision:
    """dedup_statuses is keyed by item.topic_key — the caller (pipeline.py)
    looks each one up before calling this, since that lookup is I/O and
    this function is meant to stay pure and cheap to test."""
    today = today or date.today()

    # A reply that only thanks/acknowledges/quotes posts nothing. It used
    # to post a "Parent reply to X — nothing new" notice, but those were
    # pure noise in practice (and mislabeled when staff, not a parent,
    # replied). pipeline.py still logs the skip as a reply.
    if extraction.is_reply_with_no_new_info:
        return Decision(slack_text=None, logged_items=[])

    dated_bullets: list[str] = []
    undated_bullets: list[str] = []
    logged_items: list[ExtractedItem] = []
    withheld = 0

    for item in extraction.items:
        dedup_status = dedup_statuses.get(item.topic_key, DedupStatus(already_sent=False))
        if not _should_include(item, dedup_status, config, today):
            continue

        bullet = _format_bullet(item, today, is_follow_up=dedup_status.already_sent)
        if _looks_like_it_has_a_secret(item.one_line_summary):
            # Hold back the whole bullet rather than trying to cut out
            # just the secret — a wrong guess at where it ends would
            # leak part of it. Erring here costs a pointer to the email.
            bullet = (f"- _Held back one item from \u201c{subject}\u201d — it looked like it "
                      f"contained a password or login code. Check the email directly._")
            withheld += 1
            # The sent log (synced to Drive) keeps summaries too — don't
            # store the secret there either.
            item = replace(item, one_line_summary="(held back: looked like a credential)")
        if item.deadline_date:
            dated_bullets.append(bullet)
        else:
            undated_bullets.append(bullet)
        logged_items.append(item)

    if not dated_bullets and not undated_bullets:
        return Decision(slack_text=None, logged_items=[])

    # Dated items first — easy to miss a real deadline buried after a
    # run of plain classroom-update bullets, so they lead regardless of
    # which order extraction happened to find them in.
    all_bullets = dated_bullets + undated_bullets
    text = f"*{extraction.school}*\n\n" + "\n".join(all_bullets)

    return Decision(slack_text=text, logged_items=logged_items, withheld=withheld)
