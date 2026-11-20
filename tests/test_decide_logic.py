from datetime import date

import pytest

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
    assert "• *Sep 12* · Permission slip due." in decision.slack_text
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
    assert "*Jan 15, 2027*" in decision.slack_text


def _bullet_for(summary: str, deadline_date: str) -> str:
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(deadline_date=deadline_date, one_line_summary=summary)],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    return decision.slack_text.split("\n\n", 1)[1]


@pytest.mark.parametrize("summary,deadline,expected", [
    # Real bug: extraction is told not to restate the date, but that's a
    # prompt instruction, not a guarantee. The old exact-text check only
    # caught "September 16", so abbreviated forms like these showed the
    # date twice.
    ("Unclaimed water bottles will be recycled on Oct. 30.", "2026-10-30",
     "• *Oct 30* · Unclaimed water bottles will be recycled."),
    ("Harvest festival on Oct. 30 includes a costume walk.", "2026-10-30",
     "• *Oct 30* · Harvest festival includes a costume walk."),
    ("Family picnic is Nov. 20; RSVP deadline is Nov. 6.", "2026-11-06",
     "• *Nov 6* · Family picnic is Nov. 20; RSVP deadline."),
    ("Back to School Night is on Wednesday, September 16.", "2026-09-16",
     "• *Sep 16* · Back to School Night."),
    ("Conference Day — no school for K-8. — October 28", "2026-10-28",
     "• *Oct 28* · Conference Day — no school for K-8."),
    ("Picture day (9/16) — wear the uniform.", "2026-09-16",
     "• *Sep 16* · Picture day — wear the uniform."),
    ("Permission slip due Sept. 16.", "2026-09-16",
     "• *Sep 16* · Permission slip due."),
    ("Sept. 16th: picture day.", "2026-09-16",
     "• *Sep 16* · Picture day."),
])
def test_date_already_in_summary_is_not_shown_twice(summary, deadline, expected):
    assert _bullet_for(summary, deadline) == expected


@pytest.mark.parametrize("summary,deadline", [
    # "until"/"through" say the date is an end, which the bare date up
    # front doesn't — keep the summary's wording even though it repeats.
    ("Book Fair runs through Sep. 16.", "2026-09-16"),
    ("Care available until 9/16.", "2026-09-16"),
])
def test_date_kept_in_summary_when_removing_it_would_change_the_meaning(summary, deadline):
    assert summary in _bullet_for(summary, deadline)


def test_only_the_deadline_date_is_stripped_not_a_similar_one():
    # Sep 1 must not match inside "Sep 16"
    assert _bullet_for("Forms due on Sep 1; event on Sep 16.", "2026-09-01") == \
        "• *Sep 1* · Forms due; event on Sep 16."


def test_today_in_summary_still_shows_the_date_up_front():
    """The date leads every dated bullet so the dates read as a column
    — "today" in the text is fine alongside it, and anchors the post
    when it's read later in the day or the next morning."""
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(deadline_date="2026-09-08",
                          one_line_summary="Kickoff event is today from 1:15-2:45pm.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert "• *Sep 8* · Kickoff event is today from 1:15-2:45pm." in decision.slack_text


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
                          topic_key="fall-fundraiser-2026",
                          one_line_summary="Fall fundraiser closes soon.")],
    )
    decision = decide(make_config(deadline_window_days=7), extraction,
                       {"fall-fundraiser-2026": DedupStatus(already_sent=True, last_sent_date="2026-08-01")},
                       "subj", today=TODAY)
    # already sent, but within window — should still be included (as a
    # short follow-up line, since the full summary went out before)
    assert decision.slack_text is not None
    assert "• Fall fundraiser 9/13" in decision.slack_text


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
    that dated items come first so a real deadline can't get buried
    after undated classroom notes. (Headers are now *New* / *Follow-up*,
    2026-11-20, and only appear when a post has both.)"""
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
    assert "*New*" not in decision.slack_text  # one section, no header
    # The dated item must come first regardless of extraction order
    assert decision.slack_text.index("2nd grade roundtable today") < \
        decision.slack_text.index("Room 12 started a unit")
    assert len(decision.logged_items) == 2


def test_repeat_of_ordinary_item_is_still_included_as_a_short_follow_up():
    """The double-posted field trip case: the chaperone schedule posted one evening,
    then a reminder next morning adding bag lunch / sunscreen. The repeat
    isn't dropped (topic matching is fuzzy), but it shrinks to a short
    label and date, since the full summary already went out."""
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(topic_key="pumpkin-patch-field-trip-2026",
                         one_line_summary="Field trip tomorrow — pack a nut-free lunch.",
                         deadline_date="2026-09-09")],
    )
    decision = decide(make_config(), extraction,
                      {"pumpkin-patch-field-trip-2026":
                       DedupStatus(already_sent=True, last_sent_date="2026-09-07")},
                      "subj", today=TODAY)
    assert decision.slack_text == "*Example Elementary*\n\n• Pumpkin patch field trip 9/9"
    assert len(decision.logged_items) == 1


def test_first_mention_is_shown_in_full_without_headers():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(one_line_summary="No school Monday.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert decision.slack_text == "*Example Elementary*\n\n• No school Monday."


def test_new_items_on_top_and_follow_ups_below():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[
            make_item(topic_key="water-bottle-recycling-oct30-2026", deadline_date="2026-10-30",
                      one_line_summary="Unclaimed water bottles will be recycled."),
            make_item(topic_key="picture-day", deadline_date="2026-09-16",
                      one_line_summary="Picture day — wear the uniform."),
            make_item(topic_key="no-school-teacher-workday-sept14-2026", deadline_date="2026-09-14",
                      one_line_summary="No school for a teacher workday."),
            make_item(topic_key="library-book-drive",
                      one_line_summary="The library is collecting gently used books."),
            make_item(topic_key="garden-club",
                      one_line_summary="Garden club meets on Fridays."),
        ],
    )
    sent = DedupStatus(already_sent=True, last_sent_date="2026-09-01")
    decision = decide(make_config(), extraction, {
        "water-bottle-recycling-oct30-2026": sent,
        "no-school-teacher-workday-sept14-2026": sent,
        "garden-club": sent,
        "picture-day": NOT_SENT,
        "library-book-drive": NOT_SENT,
    }, "subj", today=TODAY)
    assert decision.slack_text == (
        "*Example Elementary*\n\n"
        "*New*\n"
        "• *Sep 16* · Picture day — wear the uniform.\n"
        "• The library is collecting gently used books.\n\n"
        "*Follow-up*\n"
        "• No school teacher workday 9/14\n"
        "• Water bottle recycling 10/30\n"
        "• Garden club"
    )


@pytest.mark.parametrize("topic_key,expected", [
    ("walk-and-roll-to-school-day-2026", "Walk and roll to school day"),
    ("annual-fund-2026-27", "Annual fund"),
    ("room12-class-update-2026-10-09", "Room12 class update"),
    ("no-school-professional-day-oct9-2026", "No school professional day"),
    ("science-fair-september", "Science fair"),
])
def test_follow_up_label_drops_years_and_dates_from_topic_key(topic_key, expected):
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(topic_key=topic_key, one_line_summary="Whatever.")],
    )
    decision = decide(make_config(), extraction,
                      {topic_key: DedupStatus(already_sent=True, last_sent_date="2026-09-01")},
                      "subj", today=TODAY)
    assert decision.slack_text.endswith("• " + expected)


def test_follow_up_label_falls_back_to_summary_when_key_is_all_date():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(topic_key="2026-10-09", one_line_summary="Book fair opens in the library.")],
    )
    decision = decide(make_config(), extraction,
                      {"2026-10-09": DedupStatus(already_sent=True, last_sent_date="2026-09-01")},
                      "subj", today=TODAY)
    assert decision.slack_text.endswith("• Book fair opens in the library")


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


def test_dated_items_sort_soonest_first():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(topic_key="b", deadline_date="2026-09-20", one_line_summary="Later."),
               make_item(topic_key="a", deadline_date="2026-09-10", one_line_summary="Sooner.")],
    )
    decision = decide(make_config(), extraction, {"a": NOT_SENT, "b": NOT_SENT}, "subj", today=TODAY)
    assert decision.slack_text.index("Sooner.") < decision.slack_text.index("Later.")


def test_no_section_headers_when_only_one_kind_of_item():
    extraction = EmailExtraction(
        school="Example Elementary", is_reply_with_no_new_info=False,
        items=[make_item(one_line_summary="No school Monday.")],
    )
    decision = decide(make_config(), extraction, {"test-topic": NOT_SENT}, "subj", today=TODAY)
    assert decision.slack_text == "*Example Elementary*\n\n• No school Monday."
