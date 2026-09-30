"""Fictional sample emails used as an eval set. Made up, not real
correspondence, using the generic placeholder names from
config.example.yaml. Each entry is:

    (email, must_include: list[str], must_exclude: list[str])

must_include: substrings that MUST appear in the final decided Slack
text (or, if empty, the email is expected to produce nothing at all —
decision.slack_text should be None).
must_exclude: substrings that must NEVER appear, even if other parts of
the email are correctly included.

The single-topic cases cover the original failure modes (repeats, reply-
alls, wrong grades, volunteer scoping). The two newsletter-shaped cases
at the end are the actual point of the multi-item rebuild — modeled on
real emails (a "Head's Update", an "All-School News") that showed a
relevant item buried inside mostly-irrelevant content, which the old
one-category-per-email extraction silently dropped.
"""
from src.models import RawEmail

ROOM12_FIELD_TRIP_DEADLINE = RawEmail(
    message_id="fixture-1",
    subject="Room 12: Permission Slip Due Friday",
    sender="teacher.room12@example-elementary.org",
    body_text=(
        "Hi Room 12 families,\n\n"
        "Permission slips for our trip to the science museum are due "
        "this Friday, September 12th. Please send the signed form back "
        "with your child by then.\n\nThanks,\nMs. Rivera"
    ),
    received_at="2026-09-08T09:00:00",
)

FOURTH_GRADE_TRIP = RawEmail(
    message_id="fixture-2",
    subject="4th Grade Overnight Trip — Packing List",
    sender="office@example-elementary.org",
    body_text=(
        "Dear 4th grade families,\n\nAttached is the packing list for "
        "next month's overnight trip. Please review before the parent "
        "meeting on the 15th.\n\nBest,\nExample Elementary Office"
    ),
    received_at="2026-09-08T10:00:00",
)

REPLY_ALL_NO_NEW_INFO = RawEmail(
    message_id="fixture-3",
    subject="Re: Room 12: Permission Slip Due Friday",
    sender="another.parent@gmail.com",
    body_text=(
        "Thanks so much for the reminder!\n\n"
        "> Permission slips for our trip to the science museum are due "
        "> this Friday, September 12th."
    ),
    received_at="2026-09-08T11:00:00",
)

FUNDRAISER_REMINDER_SOON = RawEmail(
    message_id="fixture-4",
    subject="Fall Fundraiser — 5 Days Left to Order",
    sender="pto@example-elementary.org",
    body_text=(
        "Hi Example Elementary families,\n\nOur Fall Fundraiser catalog "
        "orders close this Sunday, September 13th. Get your orders in "
        "before then!\n\nThank you,\nPTO"
    ),
    received_at="2026-09-08T12:00:00",
)

LADYBUGS_CLASSROOM_UPDATE = RawEmail(
    message_id="fixture-5",
    subject="What Ladybugs Learned This Week",
    sender="teacher.ladybugs@example-preschool.org",
    body_text=(
        "Hi Ladybugs families,\n\nThis week we explored fall leaves and "
        "colors! The kids sorted leaves by shape and made leaf rubbings.\n\n"
        "Warmly,\nMs. Chen"
    ),
    received_at="2026-09-08T13:00:00",
)

VOLUNTEER_ASK_UNRELATED_CLASS = RawEmail(
    message_id="fixture-6",
    subject="Volunteers Needed: Sunflowers Fall Photos",
    sender="teacher.sunflowers@example-preschool.org",
    body_text=(
        "Hi Sunflowers families,\n\nWe need 2 volunteers to help with "
        "our fall class photos next Tuesday morning.\n\nThanks,\nMr. Patel"
    ),
    received_at="2026-09-08T14:00:00",
)

VOLUNTEER_ASK_RELEVANT_CLASS = RawEmail(
    message_id="fixture-7",
    subject="Volunteers Needed: Room 12 Halloween Party",
    sender="teacher.room12@example-elementary.org",
    body_text=(
        "Hi Room 12 families,\n\nWe're looking for 2-3 parent volunteers "
        "to help run stations at our Halloween party on October 30th.\n\n"
        "Thanks,\nMs. Rivera"
    ),
    received_at="2026-09-08T15:00:00",
)

# --- The two cases that actually justify the rebuild ---

HEADS_UPDATE_STYLE_NEWSLETTER = RawEmail(
    message_id="fixture-8",
    subject="Head's Update",
    sender="head@example-elementary.org",
    body_text=(
        "Dear Families,\n\n"
        "Thank you so much for your active engagement as we kick off "
        "this school year together. We are grateful to everyone who has "
        "attended our grade-level roundtables. Your dedication to our "
        "school community means the world to us.\n\n"
        "As I highlighted in my opening letter, helping our students "
        "become their best selves is a shared endeavor that requires "
        "clarity, intention, and aligned expectations. Over the summer, "
        "our faculty worked closely to redefine our expectations around "
        "communication, continuing values established by our founders.\n\n"
        "To ensure we are all aligned, we are asking all parents to "
        "learn directly from divisional leadership. We have created "
        "multiple opportunities to do so — please plan to attend either "
        "an in-person grade-level roundtable or the virtual option below.\n\n"
        "Virtual Session Option:\n"
        "Thursday, September 10 at 7:15 p.m. (link to join)\n\n"
        "In-Person Grade-Level Roundtables (Location: Multipurpose Room):\n"
        "2nd Grade: Tuesday, September 8 (8:30-10:00 a.m.)\n"
        "3rd Grade: Wednesday, September 9 (8:30-10:00 a.m.)\n"
        "8th Grade: Thursday, September 10 (8:30-9:45 a.m.)\n"
        "5th Grade: Friday, September 11 (8:30-9:45 a.m.)\n"
        "4th Grade: Tuesday, September 15 (8:30-10:00 a.m.)\n\n"
        "With respect and gratitude,\nHead of School"
    ),
    received_at="2026-09-08T08:00:00",
)

ALL_SCHOOL_NEWS_STYLE_NEWSLETTER = RawEmail(
    message_id="fixture-9",
    subject="Example Elementary All-School News",
    sender="news@example-elementary.org",
    body_text=(
        "NEWS & ANNOUNCEMENTS\n\n"
        "Updated 2026-27 School Calendar — we're sharing an updated copy "
        "of the school year calendar. Read more.\n\n"
        "Grandparents and Special Friends Day — Invitations will be "
        "mailed soon for November. Update grandparent mailing info by "
        "Sept 6. Read more.\n\n"
        "Collecting Kids' Clothing For Our Community Partner — help "
        "support Example Community Elementary by donating gently used kids' "
        "clothing. Read more.\n\n"
        "Upper School Back-to-School Night, 9/9 — begins at 6:00 pm.\n\n"
        "Kindergarten Parent/Guardian Reception, 9/24 — reception with "
        "the Head of School and trustees.\n\n"
        "CALENDAR:\n"
        "Sep 3 — Photo Day Grades 3, 4 & 5\n"
        "Sep 3 — 1st Grade Roundtable, 8:30-10:00 AM\n"
        "Sep 7 — Labor Day, No School\n"
        "Sep 8 — 2nd Grade Roundtable, 8:30-10:00 AM\n"
        "Sep 9 — 3rd Grade Roundtable, 8:30-10:00 AM\n"
        "Sep 9 — Upper School Back-to-School Night, 5:30-8:15 PM\n"
        "Sep 10 — 8th Grade Roundtable, 8:30-9:45 AM\n"
    ),
    received_at="2026-09-03T15:30:00",
)


MIXED_PAST_AND_FUTURE_NEWSLETTER = RawEmail(
    message_id="fixture-10",
    subject="Example Elementary All-School News (September Digest)",
    sender="news@example-elementary.org",
    body_text=(
        "NEWS & ANNOUNCEMENTS\n\n"
        "Updated School Calendar — we're sharing an updated copy of the "
        "school year calendar. Read more.\n\n"
        "Grandparents and Special Friends Day — invitations mailed soon "
        "for November. Update grandparent mailing info by Sept 6. Read more.\n\n"
        "Collecting Kids' Clothing For Our Community Partner — help "
        "support Example Community Elementary. Read more.\n\n"
        "LOWER & UPPER SCHOOL\n"
        "Upper School Back-to-School Night, 9/9 — begins at 6:00 pm.\n\n"
        "Room 5 (Kindergarten) Parent/Guardian Reception, 9/24 — "
        "reception with the Head of School and trustees.\n\n"
        "AFTERSCHOOL PROGRAMS\n"
        "Fall Afterschool Enrichment Starts Tuesday, 9/8 — some classes still have "
        "space available.\n\n"
        "CALENDAR:\n"
        "Sep 3 — Photo Day Grades 3, 4 & 5\n"
        "Sep 3 — 1st Grade Roundtable, 8:30-10:00 AM\n"
        "Sep 4 — Photo Day Grades K, 1 & 2\n"
        "Sep 6 — Grandparents mailing info update deadline\n"
        "Sep 7 — Labor Day, No School\n"
        "Sep 8 — Room 12 (2nd Grade) Roundtable, 8:30-10:00 AM\n"
        "Sep 9 — 3rd Grade Roundtable, 8:30-10:00 AM\n"
        "Sep 9 — Upper School Back-to-School Night, 5:30-8:15 PM\n"
        "Sep 10 — 8th Grade Roundtable, 8:30-9:45 AM\n"
    ),
    received_at="2026-09-03T15:30:00",
)


# (email, must_include substrings, must_exclude substrings)
IMAGE_ONLY_INVITE = RawEmail(
    message_id="fixture-11",
    subject="Room 5 Family Reception",
    sender="head@example-elementary.org",
    body_text=(
        "Room 5 Families,\n\n"
        "Come connect with the Head of School and Trustees, and others "
        "in your grade, at the Head's Residence!\n\n"
        "RSVP HERE"
        # Real emails like this put the actual date/time/location inside
        # a graphic image, which isn't part of what extraction ever
        # sees — the text body genuinely has no concrete specifics.
    ),
    received_at="2026-08-28T19:01:00",
)

FRIDAY_NEWSLETTER_NO_SPECIFICS = RawEmail(
    message_id="fixture-12",
    subject="Friday Newsletter",
    sender="teacher.room5@example-elementary.org",
    body_text=(
        "Happy Friday to our Room 5 Community! Please enjoy our "
        "newsletter this week! Have a lovely 3 day weekend!"
        # Deliberately minimal — the only test here is whether the model
        # invents a specific return date via its own calendar math
        # ("3-day weekend after Friday" = Tuesday), which it should not
        # do even though the math happens to be correct.
    ),
    received_at="2026-09-04T15:04:00",
)

MULTI_SUBJECT_CLASSROOM_UPDATE = RawEmail(
    message_id="fixture-13",
    subject="Room 12 Update: 9-4-26",
    sender="teacher.room12@example-elementary.org",
    body_text=(
        "Dear Room 12 families,\n\n"
        "We completed our first full week of school! The Room 12 "
        "kiddos immersed themselves in Writers Workshop, reading, math, "
        "science, art, music, and PE!\n\n"
        "Writing: This week the authors continued their 'I Like It "
        "When' booklets inspired by a sweet read-aloud. We also "
        "introduced Journal Writing, and the authors wrote about an "
        "exciting moment or special memory from their summer.\n\n"
        "Fundations/Phonics: The class jumped into their Fundations "
        "lessons. We focused on reviewing vowel sounds and digraphs "
        "(th, ch, wh, ck).\n\n"
        "Math: We began our Bridges unit! Students created beetle "
        "glyphs to represent personal information and explored math "
        "stations with Tiles, Pattern Blocks, Unifix Cubes, and "
        "Geoboards.\n\n"
        "Fantastic Elastic Brain: We read Your Fantastic Elastic Brain. "
        "It described the role of different parts of the brain. We "
        "will start making Brain Hats next week!\n\n"
        "Storytelling: The class finished hearing their first story, "
        "Mr. Silencio! We will start Greedbuzzer next week.\n\n"
        "NOTES, REMINDERS, AND DATES:\n"
        "Please send in if you haven't: a water bottle (nozzle top), "
        "rain boots, and extra masks.\n\n"
        "Back to School Night is Wednesday, September 16th, 6:00-8:00 PM.\n\n"
        "City Park Playground Field Trip: Wednesday, "
        "October 7th, 10:30 AM-12:45 PM. Nut-free bag lunch needed. We "
        "will need volunteers — our room coordinator will email details.\n\n"
        "Have a wonderful weekend!\n"
        "Warmly,\nMs. Rivera"
    ),
    received_at="2026-09-04T17:01:00",
)

NO_SCHOOL_PROFESSIONAL_DEVELOPMENT = RawEmail(
    message_id="fixture-14",
    subject="Reminder: No School Friday",
    sender="office@example-elementary.org",
    body_text=(
        "Dear Example Elementary families,\n\n"
        "Quick reminder that there is no school this Friday, September "
        "18th, for a Professional Development Day. Teachers will be "
        "participating in training all day. Regular classes resume "
        "Monday.\n\nBest,\nExample Elementary Office"
    ),
    received_at="2026-09-15T14:00:00",
)

PRESCHOOL_ALL_SCHOOL_NEWSLETTER = RawEmail(
    message_id="fixture-15",
    subject="News from Example Preschool",
    sender="leadership@example-preschool.org",
    body_text=(
        "A note from the Director\n\n"
        "Dear Example Preschool Families,\n\n"
        "We are just under a week away from Back-to-School Night, our "
        "first all-school community event of the year!\n\n"
        "Flow for the Evening:\n"
        "6:00-6:30 p.m. | In-Classroom Experiential Learning\n"
        "6:45-7:15 p.m. | Community Mix & Mingle\n"
        "7:20-7:50 p.m. | Schoolwide Welcome & Updates\n\n"
        "Note About Parking: we anticipate a busy parking lot Thursday "
        "evening. We encourage an earlier pickup and carpooling or "
        "rideshare if possible.\n\n"
        "Merch Pop-Up: our Merch Chairs will be in the lobby from "
        "3:00-4:30 p.m. with discounted merchandise for sale.\n\n"
        "Upcoming Events\n"
        "Thursday, 9/10 — No School, Labor Day\n"
        "Thursday, 9/10 — 3-4:30 PM Merch Pop-Up in Lobby; 6-8 PM Back "
        "to School Night\n"
        "Friday, 9/11 — 3-4 PM Parent Association Meeting in the Meadow\n"
        "Wednesday, 9/16 — Coffee Chat with the Director, 8:45-9:45 AM "
        "(updated time)\n"
        "Thursday, 9/17 — 9-10 AM Parent Education Series: School "
        "Values & Inquiry in Action (families of all ages welcome)\n"
        "Friday, 9/18 — No School, Professional Development Day\n"
        "Thursday, 10/1 — 6-7:30 PM Parent Education Series: "
        "Kindergarten Readiness (Dragonflies, Grasshoppers, and Bumblebees families "
        "welcome)\n\n"
        "Admissions Update\n"
        "The sibling process for Fall 2027 has begun. Complete the "
        "Sibling Interest Form by Thursday, September 10th if "
        "interested.\n"
        "Our school tours and events open for prospective families "
        "mid-September! In-Person Tours: Tuesdays, 9-11 AM, starting "
        "10/06/2026. Open House: Saturday, 11/07/2026, 10:00 AM-12:00 PM.\n\n"
        "Parent Association\n"
        "Join our Parent Association WhatsApp Community to connect "
        "with other families and hear about volunteer opportunities.\n\n"
        "Curriculum Corner\n"
        "Our goal for Back to School Night is for you to step inside "
        "your child's classroom. Observe how teachers listen, step in, "
        "and wait. This month, do what educators do every day: "
        "Observe, Wonder, Question, Reflect.\n\n"
        "Coffee Chat Update\n"
        "We want to acknowledge that two different start times were "
        "communicated for our Coffee Chat series. With that in mind, "
        "all upcoming Coffee Chats will take place from 8:45-9:45 AM!\n"
    ),
    received_at="2026-09-04T17:09:00",
)

VARIED_PHRASING_CLASS_MATCH = RawEmail(
    message_id="fixture-16",
    subject="Update from your little one's class",
    sender="teacher.ladybugs@example-preschool.org",
    body_text=(
        "Hi families of the ladybug classroom!\n\n"
        "Your little ladybug had a wonderful time this week exploring "
        "pumpkins and fall colors. We sorted pumpkins by size and "
        "painted with orange and yellow paint.\n\nWarmly,\nMs. Torres"
        # Deliberately never uses the literal configured string
        # "Ladybugs" anywhere — singular, lowercase, with "classroom"
        # appended instead, to test real-world phrasing tolerance.
    ),
    received_at="2026-09-04T16:00:00",
)

RELATIVE_DATE_IN_SOURCE = RawEmail(
    message_id="fixture-17",
    subject="New Bus Route Update",
    sender="transportation@example-elementary.org",
    body_text=(
        "Dear families,\n\n"
        "Please note that new bus driver Mr. Chen will be taking over "
        "Route 4 starting tomorrow. Please plan accordingly and make "
        "sure your child knows to look for a new driver at the stop.\n\n"
        "Thank you,\nTransportation Office"
        # Deliberately states ONLY "tomorrow," no literal date anywhere —
        # this has to be genuinely computed, not just copied from text.
    ),
    received_at="2026-09-07T16:00:00",  # one day BEFORE eval_live.py's
    # fixed TODAY (2026-09-08) — this gap is the whole point: "tomorrow"
    # must resolve against THIS timestamp (giving Sept 8), not against
    # today's processing date (which would wrongly give Sept 9)
)

ALL_FIXTURES = [
    (ROOM12_FIELD_TRIP_DEADLINE, ["permission slip"], []),
    (FOURTH_GRADE_TRIP, [], ["4th grade", "overnight trip"]),
    # The old section-label check here stopped meaning anything once
    # those labels were removed entirely — this now checks the thing
    # that actually still matters: a "nothing new" reply should be the
    # bare one-liner, not formatted like a real digest with a school header.
    (REPLY_ALL_NO_NEW_INFO, ["Parent reply to"], ["*Example Elementary*"]),
    (FUNDRAISER_REMINDER_SOON, ["fundraiser"], []),
    (LADYBUGS_CLASSROOM_UPDATE, ["leaves"], []),
    (VOLUNTEER_ASK_UNRELATED_CLASS, [], ["Sunflowers"]),
    (VOLUNTEER_ASK_RELEVANT_CLASS, ["Halloween"], []),
    (
        HEADS_UPDATE_STYLE_NEWSLETTER,
        ["2nd grade", "September 8"],  # the one real match, buried in filler
        ["3rd Grade", "8th Grade", "5th Grade", "4th Grade"],  # other grades must NOT leak through
    ),
    (
        ALL_SCHOOL_NEWS_STYLE_NEWSLETTER,
        ["no school", "labor day"],  # now requiring the actual reason, not
                        # just the bare fact — this used to be weakened to
                        # only "no school" because "Labor Day" was
                        # inconsistent; the prompt fix should make it reliable
        ["1st Grade Roundtable", "3rd Grade Roundtable", "8th Grade Roundtable",
         "Photo Day Grades 3", "Upper School"],  # unrelated grades must NOT leak through
    ),
    (
        MIXED_PAST_AND_FUTURE_NEWSLETTER,
        # The actual question: does a genuinely future, relevant item survive
        # in a newsletter otherwise full of past-dated and wrong-grade noise —
        # or does the past content cause the whole email to come back empty?
        ["September 24"],
        # Precise phrases, not bare grade numbers: "Photo Day Grades K, 1 & 2"
        # legitimately applies to this family's kindergarten AND 2nd grade
        # classes, so "1st Grade" and "Photo Day" correctly appear in that
        # item's summary — only the ENTIRELY-irrelevant lines should be gone.
        ["1st Grade Roundtable", "3rd Grade Roundtable", "8th Grade Roundtable",
         "Photo Day Grades 3", "Upper School"],
    ),
    (
        IMAGE_ONLY_INVITE,
        # Can't assert what SHOULD be there — an honest "see the email"
        # pointer has many valid phrasings. Only what must NOT be:
        # no fabricated specifics, no narrated uncertainty about the gap.
        [],
        ["September", "6:30", "6:00", "7:00", "not provided", "not visible",
         "no date"],
    ),
    (
        FRIDAY_NEWSLETTER_NO_SPECIFICS,
        [],
        # The exact real bug: inventing "resumes Tuesday" from "3-day
        # weekend" calendar math the email itself never actually states.
        ["Tuesday", "resumes", "not provided", "not visible", "no date"],
    ),
    (
        MULTI_SUBJECT_CLASSROOM_UPDATE,
        # The actionable items must survive as their own distinct facts —
        # consolidation should never eat a real date. Item COUNT (is it
        # really one classroom_update item, not five) isn't checkable via
        # substrings — read the printed item list for that part.
        ["September 16", "October 7"],
        [],
    ),
    (
        NO_SCHOOL_PROFESSIONAL_DEVELOPMENT,
        # A different reason than Labor Day, deliberately — confirms the
        # fix generalizes rather than just pattern-matching the one
        # example this whole conversation has repeatedly used.
        ["professional development"],
        [],
    ),
    (
        PRESCHOOL_ALL_SCHOOL_NEWSLETTER,
        # Two things at once: does the schoolwide event survive with the
        # right date (no grade table to search here, unlike the Example
        # Elementary newsletters), and does the just-shipped reason-naming fix hold on
        # a second, independent real-world "Professional Development
        # Day" instance.
        ["September 10", "professional development"],
        # Kindergarten Readiness is explicitly scoped to three OTHER
        # specific classes, named in prose rather than a table — this
        # family's own class is never mentioned anywhere in the email,
        # so correctly excluding this is a genuinely different pattern
        # than "wrong grade number" exclusion tested elsewhere.
        ["Dragonflies", "Grasshoppers", "Bumblebees", "prospective", "Open House"],
    ),
    (
        VARIED_PHRASING_CLASS_MATCH,
        # The literal configured string "Ladybugs" never appears in this
        # email at all — only "ladybug classroom," singular and
        # lowercase. If this gets excluded as irrelevant, matching is
        # too literal and needs fixing, not just this test.
        ["pumpkins"],
        [],
    ),
    (
        RELATIVE_DATE_IN_SOURCE,
        # The real bug: "tomorrow" must resolve against the email's OWN
        # Received timestamp (Sept 7 here), giving Sept 8 — not against
        # eval_live.py's processing-time TODAY (Sept 8), which would
        # wrongly compute Sept 9. The word "tomorrow" itself is fine to
        # keep; what must be correct is the actual computed date.
        ["bus", "September 8"],
        ["September 9"],
    ),
]
