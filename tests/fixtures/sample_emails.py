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
at the end are the actual point of the multi-item rebuild — a "Head's
Update" and an "All-School News", each with one relevant item buried
inside mostly-irrelevant content, which the old one-category-per-email
extraction silently dropped.
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
        "with your child by then.\n\nThanks,\nMs. Example"
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

PANDAS_CLASSROOM_UPDATE = RawEmail(
    message_id="fixture-5",
    subject="What Pandas Learned This Week",
    sender="teacher.pandas@example-preschool.org",
    body_text=(
        "Hi Pandas families,\n\nThis week we explored fall leaves and "
        "colors! The kids sorted leaves by shape and made leaf rubbings.\n\n"
        "Warmly,\nMs. Sample"
    ),
    received_at="2026-09-08T13:00:00",
)

VOLUNTEER_ASK_UNRELATED_CLASS = RawEmail(
    message_id="fixture-6",
    subject="Volunteers Needed: Koalas Fall Photos",
    sender="teacher.koalas@example-preschool.org",
    body_text=(
        "Hi Koalas families,\n\nWe need 2 volunteers to help with "
        "our fall class photos next Tuesday morning.\n\nThanks,\nMr. Placeholder"
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
        "Thanks,\nMs. Example"
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
        "What a busy start to the year! Thanks to all of you who have "
        "already come to a grade-level roundtable — it has been great "
        "to see so many familiar and new faces.\n\n"
        "A strong year depends on families and teachers working from "
        "the same playbook. Our teachers spent part of the summer "
        "updating how we share news with you and what you can expect "
        "to hear from us, and when.\n\n"
        "We'd like every parent to hear about these updates firsthand "
        "from their grade-level team. Please come to one in-person "
        "roundtable for your child's grade, or join the virtual session "
        "below if that works better.\n\n"
        "Virtual Session Option:\n"
        "Thursday, September 10 at 7:15 p.m. (link to join)\n\n"
        "In-Person Grade-Level Parent Meetings (Location: Multipurpose Room):\n"
        "3rd Grade: Tuesday, September 8 (8:30-10:00 a.m.)\n"
        "2nd Grade: Wednesday, September 9 (8:30-10:00 a.m.)\n"
        "8th Grade: Thursday, September 10 (8:30-9:45 a.m.)\n"
        "6th Grade: Friday, September 11 (8:30-9:45 a.m.)\n"
        "4th Grade: Tuesday, September 15 (8:30-10:00 a.m.)\n\n"
        "See you soon,\nHead of School"
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
        "Middle School Back-to-School Night, 9/10 — begins at 6:00 pm.\n\n"
        "5th Grade Parent/Guardian Reception, 9/23 — reception with "
        "the Head of School and trustees.\n\n"
        "CALENDAR:\n"
        "Sep 3 — Photo Day Grades 1, 2 & 4\n"
        "Sep 3 — 1st Grade Parent Meeting, 8:30-10:00 AM\n"
        "Sep 7 — Labor Day, No School\n"
        "Sep 8 — 3rd Grade Parent Meeting, 8:30-10:00 AM\n"
        "Sep 9 — 2nd Grade Parent Meeting, 8:30-10:00 AM\n"
        "Sep 10 — Middle School Back-to-School Night, 6:00-8:00 PM\n"
        "Sep 10 — 8th Grade Parent Meeting, 8:30-9:45 AM\n"
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
        "LOWER & MIDDLE SCHOOL\n"
        "Middle School Back-to-School Night, 9/10 — begins at 6:00 pm.\n\n"
        "Room 5 (5th Grade) Parent/Guardian Reception, 9/23 — "
        "reception with the Head of School and trustees.\n\n"
        "AFTERSCHOOL PROGRAMS\n"
        "Fall Afterschool Enrichment Starts Tuesday, 9/8 — some classes still have "
        "space available.\n\n"
        "CALENDAR:\n"
        "Sep 3 — Photo Day Grades 1, 2 & 4\n"
        "Sep 3 — 1st Grade Parent Meeting, 8:30-10:00 AM\n"
        "Sep 4 — Photo Day Grades K, 3 & 5\n"
        "Sep 6 — Grandparents mailing info update deadline\n"
        "Sep 7 — Labor Day, No School\n"
        "Sep 8 — Room 12 (3rd Grade) Parent Meeting, 8:30-10:00 AM\n"
        "Sep 9 — 2nd Grade Parent Meeting, 8:30-10:00 AM\n"
        "Sep 10 — Middle School Back-to-School Night, 6:00-8:00 PM\n"
        "Sep 10 — 8th Grade Parent Meeting, 8:30-9:45 AM\n"
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
        "in your grade, at a family's home!\n\n"
        "RSVP HERE"
        # Emails like this often put the actual date/time/location inside
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
        "Writing: This week the authors continued their all-about-me "
        "booklets. We also introduced Journal Writing, and the authors "
        "wrote about a favorite memory from their summer.\n\n"
        "Phonics: The class jumped into their phonics lessons. We "
        "focused on reviewing vowel sounds and digraphs "
        "(th, ch, wh, ck).\n\n"
        "Math: We began our first math unit! Students made leaf "
        "rubbings to sort and count, and explored math stations with "
        "pattern blocks, linking cubes, and geoboards.\n\n"
        "Brain Unit: We read a picture book about how the brain learns "
        "and grows. We will start making paper crowns next week!\n\n"
        "Storytelling: The class finished their first read-aloud story "
        "and will start a new one next week.\n\n"
        "NOTES, REMINDERS, AND DATES:\n"
        "Please send in if you haven't: a water bottle (nozzle top), "
        "rain boots, and extra masks.\n\n"
        "Back to School Night is Thursday, September 17th, 5:30-7:00 PM.\n\n"
        "Park Field Trip: Thursday, "
        "October 22nd, 9:30 AM-12:00 PM. Nut-free bag lunch needed. We "
        "will need volunteers — our room coordinator will email details.\n\n"
        "Have a wonderful weekend!\n"
        "Warmly,\nMs. Example"
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
        "25th, for a Professional Development Day. Teachers will be "
        "participating in training all day. Regular classes resume "
        "Monday.\n\nBest,\nExample Elementary Office"
    ),
    received_at="2026-09-22T14:00:00",
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
        "5:30-6:00 p.m. | Classroom Visits\n"
        "6:15-6:45 p.m. | Community Social\n"
        "6:50-7:20 p.m. | Welcome & Updates from the Director\n\n"
        "Note About Parking: we anticipate a busy parking lot Wednesday "
        "evening. We encourage an earlier pickup and carpooling or "
        "rideshare if possible.\n\n"
        "T-Shirt Sale: Parent Association volunteers will be in the "
        "lobby from 2:30-4:00 p.m. with school t-shirts for sale.\n\n"
        "Upcoming Events\n"
        "Monday, 9/7 — No School, Labor Day\n"
        "Wednesday, 9/9 — 2:30-4 PM T-Shirt Sale in Lobby; 5:30-7:30 PM "
        "Back to School Night\n"
        "Friday, 9/11 — 3:30-4:30 PM Parent Association Meeting on the "
        "playground\n"
        "Tuesday, 9/15 — Coffee with the Director, 8:15-9:00 AM "
        "(updated time)\n"
        "Thursday, 9/17 — 9-10 AM Parent Workshop: Supporting Play at "
        "Home (families of all ages welcome)\n"
        "Friday, 9/25 — No School, Professional Development Day\n"
        "Thursday, 10/8 — 6-7:30 PM Parent Workshop: "
        "Kindergarten Readiness (Foxes, Owls, and Turtles families "
        "welcome)\n\n"
        "Admissions Update\n"
        "The sibling process for Fall 2027 has begun. Complete the "
        "Sibling Interest Form by Friday, September 11th if "
        "interested.\n"
        "Our school tours and events open for prospective families "
        "mid-September! In-Person Tours: Wednesdays, 9:30-10:30 AM, "
        "starting 10/14/2026. Open House: Saturday, 11/14/2026, "
        "9:00-11:00 AM.\n\n"
        "Parent Association\n"
        "Join our parent group chat to connect with other families and "
        "hear about volunteer opportunities.\n\n"
        "Curriculum Corner\n"
        "Our goal for Back to School Night is for you to step inside "
        "your child's classroom and see a typical day from your child's "
        "point of view.\n\n"
        "Coffee with the Director Update\n"
        "We shared two different start times for our Coffee with the "
        "Director series. To clear that up, all upcoming sessions will "
        "run from 8:15-9:00 AM!\n"
    ),
    received_at="2026-09-04T17:09:00",
)

VARIED_PHRASING_CLASS_MATCH = RawEmail(
    message_id="fixture-16",
    subject="Update from your little one's class",
    sender="teacher.pandas@example-preschool.org",
    body_text=(
        "Hi families of the panda classroom!\n\n"
        "Your little panda had a wonderful time this week exploring "
        "pumpkins and fall colors. We sorted pumpkins by size and "
        "painted with orange and yellow paint.\n\nWarmly,\nMs. Sample"
        # Deliberately never uses the literal configured string
        # "Pandas" anywhere — singular, lowercase, with "classroom"
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
        "Please note that new bus driver Mr. Sample will be taking over "
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

ANNUAL_GIVING_KICKOFF = RawEmail(
    message_id="fixture-18",
    subject="Annual Giving Kicks Off Today!",
    sender="development@example-elementary.org",
    body_text=(
        "Dear families,\n\n"
        "Our 2026-2027 Annual Giving Campaign is live now through "
        "October 30. Look for a pledge letter in your inbox this "
        "evening.\n\n"
        "Join us for the Annual Giving kickoff today from 2:30-4pm in "
        "the gym, with snacks. Check your email for an invitation with "
        "more details.\n\n"
        "Thank you,\nDevelopment Office"
        # A two-part announcement that tends to come out as two bullets
        # ("campaign is live..." and "kickoff is today...") repeating
        # "Annual Giving".
    ),
    received_at="2026-09-08T08:00:00",  # same day as eval_live.py's TODAY
)

ALL_FIXTURES = [
    (ROOM12_FIELD_TRIP_DEADLINE, ["permission slip"], []),
    (FOURTH_GRADE_TRIP, [], ["4th grade", "overnight trip"]),
    # A "nothing new" reply posts nothing at all (no notice, no digest).
    (REPLY_ALL_NO_NEW_INFO, [], ["*Example Elementary*", "Parent reply to"]),
    (FUNDRAISER_REMINDER_SOON, ["fundraiser"], []),
    (PANDAS_CLASSROOM_UPDATE, ["leaves"], []),
    (VOLUNTEER_ASK_UNRELATED_CLASS, [], ["Koalas"]),
    (VOLUNTEER_ASK_RELEVANT_CLASS, ["Halloween"], []),
    (
        HEADS_UPDATE_STYLE_NEWSLETTER,
        ["3rd grade", "September 8"],  # the one real match, buried in filler
        ["2nd Grade", "8th Grade", "6th Grade", "4th Grade"],  # other grades must NOT leak through
    ),
    (
        ALL_SCHOOL_NEWS_STYLE_NEWSLETTER,
        ["no school", "labor day"],  # now requiring the actual reason, not
                        # just the bare fact — this used to be weakened to
                        # only "no school" because "Labor Day" was
                        # inconsistent; the prompt fix should make it reliable
        ["1st Grade Parent Meeting", "2nd Grade Parent Meeting", "8th Grade Parent Meeting",
         "Photo Day Grades 1", "Middle School"],  # unrelated grades must NOT leak through
    ),
    (
        MIXED_PAST_AND_FUTURE_NEWSLETTER,
        # The actual question: does a genuinely future, relevant item survive
        # in a newsletter otherwise full of past-dated and wrong-grade noise —
        # or does the past content cause the whole email to come back empty?
        ["September 23"],
        # Precise phrases, not bare grade numbers: "Photo Day Grades K, 3 & 5"
        # legitimately applies to this family's 3rd AND 5th grade
        # classes, so "Photo Day" and a stray "Grades K" correctly appear
        # in that item's summary — only the ENTIRELY-irrelevant lines
        # should be gone.
        ["1st Grade Parent Meeting", "2nd Grade Parent Meeting", "8th Grade Parent Meeting",
         "Photo Day Grades 1", "Middle School"],
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
        ["September 17", "October 22"],
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
        # a second, independently worded "Professional Development
        # Day" instance.
        ["September 9", "professional development"],
        # Kindergarten Readiness is explicitly scoped to three OTHER
        # specific classes, named in prose rather than a table — this
        # family's own class is never mentioned anywhere in the email,
        # so correctly excluding this is a genuinely different pattern
        # than "wrong grade number" exclusion tested elsewhere.
        ["Foxes", "Owls", "Turtles", "prospective", "Open House"],
    ),
    (
        VARIED_PHRASING_CLASS_MATCH,
        # The literal configured string "Pandas" never appears in this
        # email at all — only "panda classroom," singular and
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
    (
        ANNUAL_GIVING_KICKOFF,
        # One announcement with parts (campaign, kickoff, letter) should
        # be ONE bullet. Count isn't checkable via substrings — read the
        # printed item list. Here: the kickoff (soonest) and the campaign
        # end date both survive in whatever bullet(s) come out.
        ["2:30", "October 30"],
        [],
    ),
]
