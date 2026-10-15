from datetime import date

from src.config import Config, Rules
from src.decide import decide
from src.models import DedupStatus, EmailExtraction, ExtractedItem

TODAY = date(2026, 9, 8)


def make_config(deadline_window_days=7, volunteer_scoped=True) -> Config:
    return Config(
        schools=[],
        rules=Rules(
            deadline_window_days=deadline_window_days,
            volunteer_asks_only_for_relevant_classes=volunteer_scoped,
            skip_unrelated_grades=True,
            dedup_lookback_days=21,
        ),
        slack_channel="#test",
        extract_model="claude-haiku-4-5-20251001",
        gmail_label="School",
        db_path=":memory:",
    )


def make_item(**overrides) -> ExtractedItem:
    defaults = dict(
        requests_volunteer_help=False,
        is_promotional=False,
        classes_mentioned=[],
        relevant_classes_mentioned=[],
        deadline_date=None,
        topic_key="test-topic",
        one_line_summary="Something happened.",
    )
    defaults.update(overrides)
    return ExtractedItem(**defaults)


NOT_SENT = DedupStatus(already_sent=False)


def test_item_with_neither_flag_set_is_always_included():
    """Neither flag applies to most items — schedule changes, deadlines,
    routine updates, announcements, and anything genuinely new a future
    email might contain that doesn't fit any label at all. This is
    intentionally the default, not something each new kind of content
    needs to be added to a list to receive."""
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(one_line_summary="No school Monday.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert decision.slack_text is not None
    assert "No school Monday" in decision.slack_text


def test_deadline_is_always_included():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(deadline_date="2026-09-12",
                          one_line_summary="Permission slip due.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert "Permission slip due" in decision.slack_text
    assert "September 12" in decision.slack_text
    # Same-year dates shouldn't show the year — it's just noise for near-term school dates
    assert "2026" not in decision.slack_text
    # And the raw machine-readable date shouldn't leak into parent-facing text at all
    assert "2026-09-12" not in decision.slack_text


def test_deadline_date_shows_year_when_it_differs_from_today():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(deadline_date="2027-01-15", one_line_summary="Winter form due.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert "January 15, 2027" in decision.slack_text


def test_date_already_in_summary_is_not_duplicated_by_the_suffix():
    """Real bug: extraction is told not to restate the date, but that's
    a prompt instruction, not a guarantee — this is the deterministic
    backstop for whenever it slips through anyway."""
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(deadline_date="2026-09-16",
                          one_line_summary="Back to School Night is on Wednesday, September 16.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    # The date appears exactly once — not appended a second time
    assert decision.slack_text.count("September 16") == 1


def test_today_in_summary_drops_the_redundant_date_suffix():
    """Real case: a summary saying an event was "today" also got the
    date appended, so it said the same day twice."""
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(deadline_date="2026-09-08",
                          one_line_summary="Kickoff event is today from 1:15-2:45pm."),
               make_item(topic_key="other", deadline_date="2026-09-09",
                          one_line_summary="Picture day is tomorrow.")],
    )
    statuses = {"test-topic": NOT_SENT, "other": NOT_SENT}
    decision = decide(make_config(), extraction, statuses, "subj", today=TODAY)
    assert "September 8" not in decision.slack_text
    assert "September 9" not in decision.slack_text


def test_stale_today_keeps_the_real_date():
    """If the email sat a day, "today" is wrong — the date is the only
    thing that tells the reader so, so it must stay."""
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(deadline_date="2026-09-07",
                          one_line_summary="Kickoff event is today from 1:15-2:45pm.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert "September 7" in decision.slack_text


def test_volunteer_ask_included_when_relevant_class():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(requests_volunteer_help=True, relevant_classes_mentioned=["Room 12"],
                          one_line_summary="Need Room 12 volunteers.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert decision.slack_text is not None
    assert "Room 12 volunteers" in decision.slack_text


def test_volunteer_ask_excluded_when_no_relevant_class():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(requests_volunteer_help=True, classes_mentioned=["Koalas"],
                          relevant_classes_mentioned=[],
                          one_line_summary="Need Koalas volunteers.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert decision.slack_text is None


def test_volunteer_ask_included_when_genuinely_schoolwide():
    """Real bug this guards against: a general, whole-school volunteer
    ask (sign up for an email list, monthly snack drop-off) got
    excluded just for not naming a specific class — but nothing being
    named isn't the same situation as the wrong grade being named.
    Schoolwide content is relevant by default, same as everywhere else
    in this project; it shouldn't need to clear an extra bar just for
    being about volunteering specifically."""
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(requests_volunteer_help=True, classes_mentioned=[],
                          relevant_classes_mentioned=[],
                          one_line_summary="Sign up for our volunteer email list.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert decision.slack_text is not None
    assert "volunteer email list" in decision.slack_text


def test_volunteer_ask_included_regardless_when_rule_disabled():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(requests_volunteer_help=True, relevant_classes_mentioned=[])],
    )
    decision = decide(make_config(volunteer_scoped=False), extraction,
                       {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert decision.slack_text is not None


def test_fundraiser_included_within_deadline_window():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(is_promotional=True, deadline_date="2026-09-13",
                          one_line_summary="Fall fundraiser closes soon.")],
    )
    decision = decide(make_config(deadline_window_days=7), extraction,
                       {"test-topic": DedupStatus(already_sent=True, last_sent_date="2026-08-01")},
                       "subj", today=TODAY)
    # already sent, but within window — should still be included
    assert decision.slack_text is not None
    assert "Fall fundraiser closes soon" in decision.slack_text


def test_fundraiser_excluded_when_outside_window_and_already_sent():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(is_promotional=True, deadline_date="2026-12-01",
                          one_line_summary="Winter fundraiser.")],
    )
    decision = decide(make_config(deadline_window_days=7), extraction,
                       {"test-topic": DedupStatus(already_sent=True, last_sent_date="2026-09-01")},
                       "subj", today=TODAY)
    assert decision.slack_text is None


def test_fundraiser_included_outside_window_when_genuinely_new():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(is_promotional=True, deadline_date="2026-12-01",
                          one_line_summary="Winter fundraiser announced.")],
    )
    decision = decide(make_config(deadline_window_days=7), extraction,
                       {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert decision.slack_text is not None
    assert "Winter fundraiser announced" in decision.slack_text


def test_volunteer_help_and_promotional_both_gate_the_same_item():
    """The whole reason these are two independent flags instead of one
    category: something can be both at once -- 'volunteers needed to
    run the fundraiser table' -- and each condition has to be checked
    on its own terms rather than one topic silently winning over the
    other."""
    config = make_config(deadline_window_days=7, volunteer_scoped=True)

    # Fails the class-relevance gate alone -> excluded even though it's
    # within the deadline window
    excluded = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(requests_volunteer_help=True, is_promotional=True,
                          classes_mentioned=["4th Grade"], relevant_classes_mentioned=[],
                          deadline_date="2026-09-13",
                          one_line_summary="Fundraiser table volunteers needed.")],
    )
    decision = decide(config, excluded, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert decision.slack_text is None

    # Passes both gates -> included
    included = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(requests_volunteer_help=True, is_promotional=True,
                          relevant_classes_mentioned=["Room 12"], deadline_date="2026-09-13",
                          one_line_summary="Fundraiser table volunteers needed.")],
    )
    decision = decide(config, included, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert decision.slack_text is not None


def test_reply_with_no_new_info_short_circuits_everything():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=True,
        items=[make_item(one_line_summary="Should never appear.")],
    )
    decision = decide(make_config(), extraction, {}, "Permission Slip Due Friday", today=TODAY)
    # Posts nothing at all — no "nothing new" notice, no items.
    assert decision.slack_text is None
    assert decision.logged_items == []


def test_empty_items_list_results_in_skip():
    extraction = EmailExtraction(school="Example Elementary", is_reply_with_no_new_info=False, items=[])
    decision = decide(make_config(), extraction, {}, "subj", today=TODAY)
    assert decision.slack_text is None
    assert decision.logged_items == []


def test_multiple_items_combine_with_dated_items_ordered_first():
    """This is the exact case that broke on the real 'Head's Update'
    email: a mostly-irrelevant newsletter with one real match buried
    inside it, alongside items with and without deadlines. Also checks
    the later, explicit ask: no section labels, just dated items first
    so a real deadline can't get buried after undated classroom notes."""
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[
            # Undated item listed FIRST in extraction order, on purpose —
            # output order should not just mirror extraction order.
            make_item(topic_key="brain-unit",
                      one_line_summary="Room 12 started a unit on the brain."),
            make_item(topic_key="roundtable-2nd",
                      deadline_date="2026-09-08", one_line_summary="2nd grade roundtable today."),
            make_item(requests_volunteer_help=True, topic_key="unrelated-ask",
                      classes_mentioned=["Koalas"], relevant_classes_mentioned=[],
                      one_line_summary="Should be excluded."),
        ],
    )
    dedup = {k: NOT_SENT for k in ("roundtable-2nd", "brain-unit", "unrelated-ask")}
    decision = decide(make_config(), extraction, dedup, "subj", today=TODAY)

    assert "2nd grade roundtable today" in decision.slack_text
    assert "Room 12 started a unit" in decision.slack_text
    assert "Should be excluded" not in decision.slack_text
    assert "*Dates and deadlines:*" not in decision.slack_text
    assert "*Other news:*" not in decision.slack_text
    # The dated item must come first regardless of extraction order
    assert decision.slack_text.index("2nd grade roundtable today") < \
        decision.slack_text.index("Room 12 started a unit")
    assert len(decision.logged_items) == 2


def test_repeat_of_ordinary_item_is_still_included_but_tagged_follow_up():
    """The double-posted field trip case: the chaperone schedule posted one evening,
    then a reminder next morning adding bag lunch / sunscreen. The second
    one carries details worth acting on, so it isn't dropped — just
    tagged so it's easy to skim past when it's truly a repeat."""
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(one_line_summary="Field trip tomorrow — pack a nut-free lunch.",
                         deadline_date="2026-09-09")],
    )
    decision = decide(make_config(), extraction,
                      {"test-topic": DedupStatus(already_sent=True, last_sent_date="2026-09-07")},
                      "subj", today=TODAY)
    assert decision.slack_text is not None
    assert "- _Follow-up:_ Field trip tomorrow — pack a nut-free lunch." in decision.slack_text
    assert len(decision.logged_items) == 1


def test_first_mention_is_not_tagged_follow_up():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(one_line_summary="No school Monday.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert "Follow-up" not in decision.slack_text


def test_only_the_repeated_item_in_a_mixed_email_is_tagged():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[
            make_item(topic_key="field-trip", one_line_summary="Field trip reminder."),
            make_item(topic_key="picture-day", one_line_summary="Picture day is coming."),
        ],
    )
    decision = decide(make_config(), extraction, {
        "field-trip": DedupStatus(already_sent=True, last_sent_date="2026-09-07"),
        "picture-day": NOT_SENT,
    }, "subj", today=TODAY)
    assert "- _Follow-up:_ Field trip reminder." in decision.slack_text
    assert "- Picture day is coming." in decision.slack_text


# --- credential backstop: never post something that looks like a secret ---

import pytest


def _decide_one(summary: str):
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(one_line_summary=summary),
               make_item(topic_key="other", one_line_summary="Picture day is Friday.")],
    )
    return decide(make_config(), extraction, {}, "Volunteer team login", today=TODAY)


@pytest.mark.parametrize("summary", [
    # The real slip, with made-up values: username AND password in one line.
    "A shared reporting login was set up (user TreasurerTeam, password fundraiser2026).",
    "Log in with password: hunter22",
    "The front gate code is 4417 after 6pm.",
    "Your PIN is 0042.",
    "Use username jsmith42 to sign in.",
    "Passcode = 98765 for the Zoom meeting.",
])
def test_bullet_with_a_credential_is_held_back(summary):
    decision = _decide_one(summary)
    assert summary not in decision.slack_text
    assert "Held back one item from “Volunteer team login”" in decision.slack_text
    assert "Picture day is Friday." in decision.slack_text  # the rest still posts
    assert decision.withheld == 1
    # The sent log (synced to Drive) must not get the secret either.
    assert all(summary != i.one_line_summary for i in decision.logged_items)


@pytest.mark.parametrize("summary", [
    "A shared reporting login was set up for the volunteer team — login details are in the email.",
    "Reset your portal password by Friday.",
    "Password reset instructions were sent.",
    "Parents will need a username and password to book conferences — see the email.",
    "Pin the schedule to your fridge.",
])
def test_harmless_mentions_are_not_held_back(summary):
    decision = _decide_one(summary)
    assert summary in decision.slack_text
    assert decision.withheld == 0
