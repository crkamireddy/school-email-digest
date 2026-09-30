"""Shared data structures passed between pipeline stages. Keeping these
explicit (instead of passing raw dicts around) makes each stage's contract
obvious and makes it easy to write tests against.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class RawEmail:
    """What comes in from Gmail (or a test fixture)."""
    message_id: str
    subject: str
    sender: str
    body_text: str
    received_at: str  # ISO date string


@dataclass
class ExtractedItem:
    """One distinct, potentially-relevant thing pulled out of an email.
    A single email can produce zero, one, or many of these — that's the
    whole point of the multi-item rebuild: a newsletter with ten things
    in it shouldn't be forced into one category for the whole email.

    No topic category field on purpose — decide.py never needs to know
    *what something is about*, only whether either of two independent
    conditions applies: does this only matter for a specific class, and
    is this the kind of thing that shouldn't be repeated every time it's
    mentioned. Everything else survives by default. A genuinely new kind
    of email content needs new words in one_line_summary, not a new
    category the whole system has to be taught about.
    """
    requests_volunteer_help: bool  # only matters for a specific class if
    # config.rules.volunteer_asks_only_for_relevant_classes is on —
    # gated by relevant_classes_mentioned below, not by topic
    is_promotional: bool  # likely to get re-mentioned repeatedly —
    # only include near its deadline, or the first time it's genuinely new
    classes_mentioned: list[str]
    relevant_classes_mentioned: list[str]
    deadline_date: Optional[str]
    topic_key: str
    one_line_summary: str

    @staticmethod
    def from_dict(d: dict) -> "ExtractedItem":
        return ExtractedItem(
            requests_volunteer_help=bool(d.get("requests_volunteer_help", False)),
            is_promotional=bool(d.get("is_promotional", False)),
            classes_mentioned=d.get("classes_mentioned", []),
            relevant_classes_mentioned=d.get("relevant_classes_mentioned", []),
            deadline_date=d.get("deadline_date"),
            topic_key=d["topic_key"],
            one_line_summary=d.get("one_line_summary", ""),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EmailExtraction:
    """Output of the extract stage for one whole email. Classification
    and item-pulling only — no inclusion judgment calls live here. Items
    that clearly don't matter to this family (wrong grade, pure
    marketing noise) simply never become items in the first place;
    everything that *does* become an item is a real candidate, gated
    next by real facts, not further LLM guessing.
    """
    school: str
    is_reply_with_no_new_info: bool
    items: list[ExtractedItem]
    grade_specific_scan: str = ""  # the model's own scratchpad reasoning
    # about grade-table matching — kept as real data, not discarded,
    # specifically so a wrong item can be diagnosed against what the
    # model actually found rather than guessed at from the outside.

    @staticmethod
    def from_dict(d: dict) -> "EmailExtraction":
        return EmailExtraction(
            school=d["school"],
            is_reply_with_no_new_info=bool(d.get("is_reply_with_no_new_info", False)),
            items=[ExtractedItem.from_dict(i) for i in d.get("items", [])],
            grade_specific_scan=d.get("grade_specific_scan", ""),
        )


@dataclass
class DedupStatus:
    """Ground truth from the sent-log store — not a guess."""
    already_sent: bool
    last_sent_date: Optional[str] = None


@dataclass
class Decision:
    """Output of the decide stage — now pure Python, no LLM call. See
    decide.py."""
    slack_text: Optional[str]  # None means "skip, nothing to post"
    logged_items: list[ExtractedItem]  # items to write to the sent log
    is_reply_notice: bool = False  # the "nothing new" reply case — still
    # posted, but not a real digest entry, so callers (logging, etc.)
    # shouldn't describe it in terms of item counts
