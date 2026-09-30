"""Real emails a friend shared, from schools entirely outside this
project's own family/config — genericized (names, addresses, staff
emails) the same way every fixture in this project is, but the real
content and structure kept intact. Pairs with config.friend-test.yaml.

The point isn't more coverage of the same family — it's testing whether
the category-free, flag-based design generalizes to genuinely different
schools, formats, and content types it was never tuned against. Run
with:

    python eval_live.py --config config.friend-test.yaml \
                         --fixtures tests.fixtures.friend_test_emails

This is a simulated second family (see config.friend-test.yaml) with
kids in 4th grade, kindergarten + 2nd grade, 7th grade, and 9th grade,
across four different schools.
"""
from src.models import RawEmail

NORTH_GIVING_CAMPAIGN = RawEmail(
    message_id="friend-fixture-1",
    subject="Friends of Example North Campaign",
    sender="pto@example-elementary-north.org",
    body_text=(
        "Friends of Example North Is Officially Here!\n\n"
        "We're excited to kick off Example Elementary North's annual "
        "Friends of Example North fundraising campaign!\n\n"
        "Our goal this year is to raise $20,000, with 100% of every "
        "dollar raised going directly back to Example Elementary North. "
        "Instead of selling products door-to-door or using a "
        "third-party fundraising platform, Friends of Example North allows "
        "our community to come together and directly support our "
        "students, teachers, and school. Our suggested donation is $60 "
        "per student, but gifts of any amount are welcomed.\n\n"
        "As our school reaches fundraising milestones, students will "
        "earn special theme days: $5,000 -> Pajama Day! $10,000 -> "
        "Teachers dress up like kids. $15,000 -> two staff members race "
        "in inflatable dinosaur costumes. $20,000 -> a pie in the "
        "principal's face!\n\n"
        "Bonus: the grade that donates the most will win popsicles at "
        "recess!\n\n"
        "Stay tuned for information on employer matching and how you "
        "may be able to double your impact!\n\n"
        "Donate here: https://example-north-giving.exampledonate.com\n\n"
        "Thank you!\nExample Elementary North PTO"
    ),
    received_at="2026-09-08T13:06:00",
)

GOOGLE_CLASSROOM_GUARDIAN_CONNECTION = RawEmail(
    message_id="friend-fixture-2",
    subject="Google Classroom Guardian Connection",
    sender="schoolmessenger@exampledistrict.k12.example.us",
    body_text=(
        "Dear Parents and Guardians,\n\n"
        "By the end of the week, you will receive an email invitation "
        "from Google Classroom to connect to your student's account as "
        "a guardian.\n\n"
        "Once you receive the email, please follow these brief steps: "
        "click Accept inside the email invitation, then on the page "
        "that opens, select your preferred frequency for work summary "
        "emails (e.g., Daily or Weekly).\n\n"
        "These summaries may contain classroom announcements, missing "
        "classwork, and upcoming assignments. Each teacher will "
        "communicate how Google Classroom will be used for their "
        "instructional purposes.\n\n"
        "As a reminder, parents will NOT have an observer account. "
        "Parents may log in alongside their child to view the Google "
        "Classroom.\n\n"
        "Thank you for your continued partnership and support!\n\n"
        "Example School District"
    ),
    received_at="2026-09-01T08:00:00",
    # Deliberately no school name anywhere in the body — this is a
    # genuine district-wide notice, not tied to any of the four
    # configured schools. Tests the "genuinely doesn't match any
    # configured school" fallback the prompt already describes.
)

HIGH_SCHOOL_POST_FOOTBALL_TRAFFIC = RawEmail(
    message_id="friend-fixture-3",
    subject="High School Post-Football Traffic Reminders",
    sender="noreply@exampledistrict.example-notify.com",
    body_text=(
        "Parents! If you plan to pick up your student after a football "
        "game, please read the instructions below. There is NO PICKUP "
        "allowed at the stadium. No vehicles will be able to enter the "
        "lots following the game. All student pickups are at the "
        "Aquatic Center, Door 14.\n\n"
        "As a reminder, no backpacks, bags, or sports balls are "
        "allowed.\n\n"
        "Post Football Game Traffic Information:\n"
        "All student pickups are at the Aquatic Center (Door 14) and NOT "
        "at the stadium.\n"
        "No vehicles will be permitted to enter the stadium parking "
        "lots following football games.\n"
        "Unaccompanied students should leave through the South Gate "
        "and walk to the designated pickup area.\n"
        "Adults picking up a student should enter from Main Street and "
        "pick up at the designated area.\n"
        "It will be easiest to find a parking spot and communicate "
        "with your child rather than wait in a gridlocked line.\n\n"
        "We love having our students at the games, and this plan is "
        "designed to help both fans leaving the game and adults "
        "picking up their student. Thank you for your cooperation."
    ),
    received_at="2026-09-03T12:45:00",
    # No specific grade or building named anywhere in the text either —
    # unlike the other fixtures, the real source email conveyed the
    # school itself mainly through a map image, invisible to this
    # pipeline. Genuinely ambiguous, kept as-is rather than cleaned up,
    # since a real one like this could show up for real.
)

SOUTH_FUN_RUN_UPDATE = RawEmail(
    message_id="friend-fixture-4",
    subject="Example South Fun Run Update - September 11, 2026",
    sender="frontoffice@example-elementary-south.org",
    body_text=(
        "We are just over halfway to our fundraising goal for the "
        "Example South Fun Run! This week, we surprised students with flashlight "
        "reading time, and EVERY student will receive a new t-shirt to "
        "wear on September 18th for our school-wide Fun Run "
        "celebration!\n\n"
        "September 18th Celebration - Fun Run Schedule:\n"
        "8:15am-8:45am: Track 1 - 5th Grade, Track 2 - Kindergarten\n"
        "8:50am-9:20am: Track 1 - 4th Grade, Track 2 - 2nd Grade\n"
        "9:25am-9:55am: Track 1 - 1st Grade, Track 2 - 3rd Grade\n\n"
        "There is still time to support our biggest fundraiser of the "
        "year and hit our next goal of $25,000, and overall goal of "
        "$35,000, to support amazing opportunities all year long - "
        "including FREE field trips, family fun nights, all school "
        "assemblies, and more!\n\n"
        "Please also make sure to share your student's donation link "
        "with friends and family to help spread the word!"
    ),
    received_at="2026-09-11T08:30:00",
    # Real test: this family has TWO relevant grades at this one school
    # (Kindergarten and 2nd), and they're in DIFFERENT tracks at
    # DIFFERENT times, in a table with two other, irrelevant grades
    # mixed in on the same rows. Needs both real times, correctly
    # matched, with the irrelevant grades left out.
)

NORTH_OPT_IN_DIRECTORY = RawEmail(
    message_id="friend-fixture-5",
    subject="Opt-In to the Directory Today!",
    sender="pto@example-elementary-north.org",
    body_text=(
        "Opt-In Form for Parent Directory\n\n"
        "Parents & caregivers, we know you're looking forward to "
        "setting up some playdates with your child's new friends! For "
        "privacy purposes, the district requires the student & parent "
        "directory to be OPT-IN. To opt-in, you must complete ONE "
        "Google Form and include information for EACH student that "
        "attends Example Elementary North. Your information will "
        "appear in the directory exactly as it was entered. The "
        "directories will be distributed by grade level once the "
        "collection process is complete. Please complete the opt-in "
        "form by September 30."
    ),
    received_at="2026-09-09T14:37:00",
)

MIDDLE_SCHOOL_SEPTEMBER_NEWS = RawEmail(
    message_id="friend-fixture-6",
    subject="September News: All-Parent Meeting & Check Out the Competition!",
    sender="pto@example-middle-school.org",
    body_text=(
        "Welcome to September! We've got a packed issue to keep you in "
        "the loop.\n\n"
        "We officially hit our 75% fundraising milestone! With $30,535 "
        "raised, we are close to our final $40,000 goal. 75% Milestone "
        "unlocked: our admin team is stepping behind the counter to "
        "serve lunch in the cafeteria!\n\n"
        "The Grade-Level Race is on: the team in each grade with the "
        "highest average donation per student scores an ice cream "
        "social for the kids and a catered lunch for their teachers. "
        "Current standings across all grades: 1st place 7-1 team "
        "$5,015; 2nd place 6-2 team $4,890; 3rd place 8-2 team $3,605; "
        "4th place 6-3 team $3,335; 5th place 7-2 team $3,280; 6th "
        "place 7-3 team $3,025; 7th place 6-1 team $2,075; 8th place "
        "8-3 team $2,025; 9th place 8-1 team $1,260. We want to hit "
        "our $40,000 goal by Friday, September 18th.\n\n"
        "All-Parent PTO Meeting with Special Guest, our Superintendent: "
        "please join us for our first All-Parent PTO meeting of the "
        "year! As a parent, you are automatically a member of the PTO. "
        "Date & Time: Wednesday, September 16th at 6:30 PM. Location: "
        "Example Middle School, LGI Room. Stick around until the end "
        "for a chance to win a $25 gift card raffle (must be present "
        "to win). RSVP appreciated but not required.\n\n"
        "Grab Your Gear: the spirit wear store is open all year, "
        "featuring new seasonal drops. Order by October 1st to ensure "
        "your gear arrives in late October.\n\n"
        "Stay in the Loop: the school broadcasts a student-created "
        "news show every Friday, written, filmed, and produced "
        "entirely by students.\n\n"
        "Support our Athletes: the school uses cashless, digital "
        "ticketing for all home athletic events. Tickets cannot be "
        "purchased with cash at the gate.\n\n"
        "Volunteer Opportunity: 8th Grade Vision Screening. We need "
        "4-5 volunteers to help with 8th-grade vision screenings on "
        "Monday, October 5, starting at 8:35 AM (wrapping up around "
        "10:40 AM). Requirement: an active background check on file.\n\n"
        "General Volunteer: if you'd like to help on an as-needed "
        "basis, sign up for our volunteer email list. Tuesday Treats: "
        "help us spoil our teachers and staff with a monthly drop-off "
        "of snacks. Game Shack: a lunchtime board-game cart that needs "
        "regular volunteers.\n\n"
        "Skip cooking on Wednesday, September 16th (11 AM - 10 PM) and "
        "help support the school! A local restaurant is donating 25% "
        "of proceeds back to the school that day.\n\n"
        "Important Dates & Events: All Parent PTO Meeting, Wednesday "
        "September 16, 6:30 PM. Dine to Donate, Wednesday September "
        "16. Tuesday Treats sign-up, Tuesday October 6. Dine to Donate, "
        "Wednesday October 7. Fall Break - No School, Monday October "
        "12 through Friday October 16. Book Fair - volunteer signups "
        "and more info coming soon, Friday October 23 through Friday "
        "October 30. Tuesday Treats sign-up, Tuesday November 3. Dine "
        "to Donate, Wednesday November 4. Thanksgiving Break - No "
        "School, Wednesday November 25 through Friday November 27."
    ),
    received_at="2026-09-10T09:45:00",
    # The richest, most multi-topic fixture in this batch on purpose:
    # a schoolwide meeting with a real date, a real deadline (spirit
    # wear), routine/no-action filler (the news show), a genuinely
    # wrong-grade volunteer ask (8th grade, this family has a 7th
    # grader), general non-class-specific volunteer asks, a one-time
    # dine-to-donate event, and — buried at the very bottom of a long
    # list, not called out anywhere else in the email — a real
    # schoolwide no-school week.
)

PRINCIPAL_WEEKLY_NEWSLETTER = RawEmail(
    message_id="friend-fixture-7",
    subject="The Weekly Update",
    sender="principal@example-elementary-north.org",
    body_text=(
        "Hello Example Elementary North Families,\n\n"
        "It was wonderful seeing so many of you here for our Meet the "
        "Teacher Night this past Tuesday. I enjoyed popping into many "
        "of the classrooms during the event.\n\n"
        "It's been exciting this past week to visit classrooms and "
        "watch as teachers have worked with their class to build "
        "routines, relationships, and expectations, and classes are "
        "now shifting into real curriculum work.\n\n"
        "In the time I've been in classrooms recently, here are some "
        "of the things I've noticed our students focused on: "
        "Kindergarten: identify key details and the main idea while "
        "reading My 5 Senses. First Grade: retell a story through the "
        "lens of a character. Second Grade: ask and answer questions "
        "about important details. Third Grade: how to use a story map "
        "to find the central message. Fourth Grade: identify the main "
        "idea and details about the heart while reading The "
        "Circulatory Story. Fifth Grade: summarizing the main idea and "
        "key details of a cultural studies unit.\n\n"
        "The best way you can help your child at home is by having "
        "them read - it could be you reading to them, them reading to "
        "you, or them reading independently.\n\n"
        "School Safety: staff and students have done an amazing job "
        "during our first two safety drills! Next week we will do our "
        "third drill, focused on Severe Weather protocols.\n\n"
        "Note from the Nurse: does something have your child "
        "scratching their head lately? It's always that time of year "
        "to be vigilant for head lice. Please feel free to contact the "
        "nurse for any questions or concerns.\n\n"
        "Upcoming Events: 9/2 Late Start Day (school starts at 8:20). "
        "9/7 Labor Day Holiday - schools and offices closed. 9/8 "
        "Friends of Example North Campaign begins. 9/13, 4:00-6:00 "
        "Kindergarten Play Date on the playground. 9/16 Late Start Day. "
        "9/18, 5:30-8:00 Food Truck Festival, sponsored by the PTO."
    ),
    received_at="2026-08-28T17:00:00",
    # Same school as the fundraiser and directory opt-in fixtures above
    # — a real test of whether three separate emails about the same
    # school stay consistent. Also: six grades' worth of curriculum
    # detail in one list, only one relevant; a wrong-grade playdate
    # mixed into an otherwise-relevant events list; and a genuinely new
    # kind of content this project has never seen before — a health/
    # safety notice with no clean analog among the existing categories.
)

ALL_FIXTURES = [
    (
        NORTH_GIVING_CAMPAIGN,
        # Confirmed: the per-student suggested donation ($60) is the
        # more useful number for a parent deciding whether to give —
        # the earlier check for the school-wide total ($20,000) was
        # testing my own assumption, not a real requirement.
        ["$60"],
        [],
    ),
    (
        GOOGLE_CLASSROOM_GUARDIAN_CONNECTION,
        ["observer"],
        # Real bug found: "by the end of the week" got fabricated into
        # a specific date ("September 5") that was never actually
        # stated anywhere in the email.
        ["September 5"],
    ),
    (
        HIGH_SCHOOL_POST_FOOTBALL_TRAFFIC,
        ["Door 14"],
        [],
    ),
    (
        SOUTH_FUN_RUN_UPDATE,
        ["8:15", "8:50"],
        ["5th Grade", "4th Grade", "1st Grade", "3rd Grade"],
    ),
    (
        NORTH_OPT_IN_DIRECTORY,
        ["September 30"],
        [],
    ),
    (
        MIDDLE_SCHOOL_SEPTEMBER_NEWS,
        # September 16/October 12: the meeting date, and Fall Break
        # buried at the bottom of a long list, both need to survive.
        # Tuesday Treats: real bug fixed — a genuinely schoolwide
        # volunteer ask (no specific grade named) was getting excluded
        # just for not naming a class, same bar as a wrong-grade ask.
        # "restaurant": real bug fixed — attending a dine-to-donate
        # night got flagged as requesting volunteer help, when it's
        # something to show up and pay for. Checking for the substance
        # here, not the literal program name — the model reasonably
        # paraphrased "Dine to Donate" away while keeping the actual
        # content (restaurant, date, proceeds) intact.
        ["September 16", "October 12", "Tuesday Treats", "restaurant"],
        ["vision screening", "8th Grade"],
    ),
    (
        PRINCIPAL_WEEKLY_NEWSLETTER,
        ["heart"],
        ["Kindergarten Play Date", "Kindergarten: identify"],
    ),
]
