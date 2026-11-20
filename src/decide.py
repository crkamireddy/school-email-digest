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
    """Short, e.g. 'Sep 12' — it leads the bullet as a scannable date
    column, so it stays narrow. The year only gets added when it's not
    the current year, since for typical near-term school dates it's
    just noise."""
    d = datetime.strptime(deadline_date, "%Y-%m-%d").date()
    formatted = f"{d.strftime('%b')} {d.day}"
    if d.year != today.year:
        formatted += f", {d.year}"
    return formatted


def _date_pattern(d: date) -> str:
    """Regex for the ways a summary tends to write this one date:
    'October 30', 'Oct. 30', 'Oct 30th', 'Sept. 3', '10/30', optionally
    with a weekday in front and the year after."""
    full = d.strftime("%B")
    months = {full, full[:3]} | ({"Sept"} if d.month == 9 else set())
    month = "(?:" + "|".join(sorted(months, key=len, reverse=True)) + r")\.?"
    weekday = r"(?:(?:Mon|Tues|Wednes|Thurs|Fri|Satur|Sun)day,?\s+)?"
    worded = rf"{month}\s+{d.day}(?:st|nd|rd|th)?(?!\d)(?:,?\s+{d.year})?"
    numeric = rf"{d.month}/{d.day}(?:/(?:{d.year}|{d.year % 100}))?(?![\d/])"
    return rf"{weekday}(?:{worded}|{numeric})"


def _strip_repeated_date(summary: str, deadline_date: str) -> str:
    """Backstop, not the primary fix: the extraction prompt is told not
    to restate the date, but a prompt instruction is never a guarantee.
    The date already leads the bullet, so drop the summary's copy — but
    only where the sentence still reads right without it ("recycled on
    Oct. 30" -> "recycled"). "until"/"through"/"from" are left alone on
    purpose: they mark the date as an end or start, which the bare date
    up front doesn't say, so a rare repeat beats losing that meaning."""
    d = datetime.strptime(deadline_date, "%Y-%m-%d").date()
    date_re = _date_pattern(d)
    removable = [
        rf"\s*\({date_re}\)",                               # "... (Oct. 30)"
        rf"\s+(?:is\s+)?(?:on|by)\s+{date_re}",               # "recycled on Oct. 30"
        rf"(?<=\bdue)\s+{date_re}",                            # "due Oct. 30" (keeps "due")
        rf"\s+(?:is|are)\s+{date_re}",                        # "deadline is Nov. 6"
        rf"^{date_re}\s*[:\u2014\u2013-]\s*",               # "Oct. 30: ..."
        rf"\s*[\u2014\u2013,-]\s*{date_re}(?=[.!]?$)",       # "... — Oct. 30"
    ]
    for pattern in removable:
        summary = re.sub(pattern, "", summary, flags=re.IGNORECASE)
    # Tidy what removal can leave behind: " ." / " ;" / a lowercase start.
    summary = re.sub(r"\s+([.,;!?])", r"\1", summary).strip()
    return summary[:1].upper() + summary[1:]


def _format_bullet(item: ExtractedItem, today: date) -> str:
    if not item.deadline_date:
        return f"\u2022 {item.one_line_summary}"

    formatted_date = _format_deadline_date(item.deadline_date, today)
    summary = _strip_repeated_date(item.one_line_summary, item.deadline_date)
    return f"\u2022 *{formatted_date}* \u00b7 {summary}"


_MONTH_TOKEN_RE = re.compile(
    r"^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
    r"(?:uary|ruary|ch|il|e|y|ust|tember|ober|ember)?\d*$"
)


def _short_label(item: ExtractedItem) -> str:
    """A few words naming a repeat, built from its topic_key
    ('walk-and-roll-to-school-day-2026' -> 'Walk and roll to school
    day'). topic_key already exists for matching repeats, so this costs
    nothing and needs no prompt change; the price is that a label reads
    a bit mechanically. Years, bare numbers and month-plus-day tokens
    ('oct9', 'sept11') come out, since the date is shown separately."""
    words = [w for w in item.topic_key.lower().split("-")
             if w and not w.isdigit() and not _MONTH_TOKEN_RE.match(w)]
    if not words:
        # Nothing left of the key: fall back to the summary's first words.
        words = item.one_line_summary.rstrip(".").split()[:6]
    label = " ".join(words)
    return label[:1].upper() + label[1:]


def _format_follow_up(item: ExtractedItem) -> str:
    # Repeats still post (a reminder about the field trip often adds the
    # detail you actually need, like "bring a bag lunch"), but only as a
    # short label: the full summary already went out the first time.
    # Shown rather than hidden because topic matching is fuzzy, so a
    # wrong match costs a too-short line, not a missed email.
    if not item.deadline_date:
        return f"\u2022 {_short_label(item)}"
    d = datetime.strptime(item.deadline_date, "%Y-%m-%d").date()
    return f"\u2022 {_short_label(item)} {d.month}/{d.day}"


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

    new_items: list[tuple[ExtractedItem, str]] = []  # (item, bullet)
    follow_ups: list[ExtractedItem] = []
    logged_items: list[ExtractedItem] = []
    withheld = 0

    for item in extraction.items:
        dedup_status = dedup_statuses.get(item.topic_key, DedupStatus(already_sent=False))
        if not _should_include(item, dedup_status, config, today):
            continue

        has_secret = _looks_like_it_has_a_secret(item.one_line_summary)
        if dedup_status.already_sent:
            # Only the topic_key label is shown for a repeat, never the
            # summary, so there is nothing to hold back from Slack here.
            follow_ups.append(item)
        elif has_secret:
            # Hold back the whole bullet rather than trying to cut out
            # just the secret — a wrong guess at where it ends would
            # leak part of it. Erring here costs a pointer to the email.
            held_back = (f"_Held back one item from \u201c{subject}\u201d — it looked like it "
                         f"contained a password or login code. Check the email directly._")
            bullet = (f"\u2022 *{_format_deadline_date(item.deadline_date, today)}* \u00b7 {held_back}"
                      if item.deadline_date else f"\u2022 {held_back}")
            new_items.append((item, bullet))
            withheld += 1
        else:
            new_items.append((item, _format_bullet(item, today)))
        if has_secret:
            # The sent log (synced to Drive) keeps summaries too — don't
            # store the secret there either.
            item = replace(item, one_line_summary="(held back: looked like a credential)")
        logged_items.append(item)

    if not new_items and not follow_ups:
        return Decision(slack_text=None, logged_items=[])

    # Within each section, dated items first, soonest first — easy to
    # miss a real deadline buried after a run of plain classroom-update
    # bullets. ISO dates sort correctly as plain strings, and undated
    # items sort last ("~" is after every digit); the sort is stable, so
    # ties keep extraction order.
    def by_date(item: ExtractedItem) -> str:
        return item.deadline_date or "~"

    new_lines = [bullet for _, bullet in sorted(new_items, key=lambda pair: by_date(pair[0]))]
    follow_up_lines = [_format_follow_up(item) for item in sorted(follow_ups, key=by_date)]
    # Section headers only when there are two sections to tell apart —
    # a lone "New" header over the only list in the post is noise.
    if new_lines and follow_up_lines:
        body = "*New*\n" + "\n".join(new_lines) + "\n\n*Follow-up*\n" + "\n".join(follow_up_lines)
    else:
        body = "\n".join(new_lines or follow_up_lines)
    text = f"*{extraction.school}*\n\n" + body

    return Decision(slack_text=text, logged_items=logged_items, withheld=withheld)
