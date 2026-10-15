# Decision log

This is the original author's build history: why things are the way
they are, in the order they were decided. You don't need it to set up
or run your own copy. Feel free to delete it, or keep your own entries
below.

Buckets: **cheap** = cheap to undo, noted and kept moving. **expensive** =
expensive to undo (schema, auth, real data, cost), should be paused on.

## 2026-09-15 — make-shareable branch

- **Drive folder ID moved from code to `storage.drive_folder_id` in
  config, and made optional (empty = local-only).** Why: the hardcoded
  ID was one person's folder, and a genuinely local-only setup didn't
  exist — every real run required Drive. Bucket: expensive-ish (config
  schema, touches the live dedup state), mitigated below.
- **`drive_folder_id` key is required even though its value may be
  empty; a missing key raises.** Why: an existing config.yaml (local, or
  the one in the GitHub secret) written before this change must fail
  loudly, not silently switch to local-only and abandon the shared Drive
  history. Bucket: cheap.
- **Refuse to run on GitHub Actions (detected via `GITHUB_ACTIONS=true`)
  without a Drive folder.** Why: a cloud runner's disk is blank every
  run, so local-only there means no cursor and no dedup — the same
  emails re-posted every run. Bucket: cheap.
- **OAuth still always requests both Gmail and Drive scopes, even for
  local-only.** Why: making scopes depend on config would force a
  re-authorization whenever someone switches modes; `drive.file` only
  covers files the app creates. Bucket: cheap.
- **Placeholder values in tests and the prompt use the fictional
  "Example Elementary" / "Room 12" convention; the prompt's
  class-name-matching example uses "Otters", a name not used in any
  config or fixture.** Why: using a fixture's own class name in the
  prompt would let the eval pass because the prompt spelled out the
  answer. Bucket: cheap.
- **Fixtures derived from real emails were genericized further:
  program/campaign names, mascot references, building details, sender
  domains, fixture variable names, and neighboring-school / place names
  in the "fictional" sample set.** (Superseded 2026-10-15: every
  remaining figure, date, name and program in the fixtures was replaced
  with made-up values.) Bucket: cheap.
- **MIT license, copyright holder taken from the git author name.**
  Bucket: cheap.
- **`.DS_Store` files untracked and gitignored.** Why: Finder metadata
  can reveal local folder and file names. Bucket: cheap.
- **Known cross-machine timezone issue documented in README rather than
  fixed.** Why: out of scope for this branch and changes live cursor
  behavior; flagged for a separate decision. Bucket: expensive (real
  data).

## 2026-09-15 — config builder

- **Config builder is a single self-contained local HTML file
  (`tools/config-builder.html`), not a hosted page or an Artifact.** Why:
  runs offline with no server and no external scripts, so school and
  class names never leave the user's computer; hosted Artifacts also
  can't trigger file downloads. Bucket: cheap.
- **YAML is written by hand in JavaScript, every string double-quoted
  and escaped, rather than via a YAML library.** Why: a library would
  mean loading an external script; the format is small and fixed.
  Verified by loading builder output (including quotes, apostrophes, and
  a backslash in names) with the real `load_config()`. Bucket: cheap.
- **`skip_unrelated_grades` isn't asked; the builder always writes
  `true`.** Why: the loader requires the key but no code reads it, so a
  visible toggle would do nothing. Bucket: cheap.
- **Model choice is a hardcoded two-item list (Haiku 4.5 default, Sonnet
  5), under Advanced.** Needs updating when models change. Bucket: cheap.
- **The builder refuses Gmail labels with spaces/slashes, invalid Slack
  channel names, and duplicate school names; it accepts a full Drive
  folder URL and extracts the ID.** Why: each would otherwise produce a
  config that loads but silently misbehaves (broken Gmail search,
  unresolvable channel, merged dedup history). Bucket: cheap.
- **Added a pytest guard that every key in `config.example.yaml` appears
  in the builder's output code.** Why: catches the most likely drift (a
  new config key the builder never writes) without running JavaScript
  in the test suite. Doesn't catch a changed value format. Bucket: cheap.
- **Slack channel is entered as a channel ID (e.g. C0123456789), not a
  name — in the builder, config.example.yaml, and README.** Why: user
  request; also means the Slack app only needs `chat:write`, since IDs
  skip the name lookup that requires `channels:read`. Names still work
  in a hand-edited config (no Python change). The builder accepts a
  pasted channel link and extracts the ID, but does NOT uppercase
  lowercase input, since a lowercase channel name could then pass as an
  ID. Placeholder is a fake ID, not the user's own. Bucket: cheap.

## 2026-09-30

- **Diagnosis: daily failures were Google OAuth `invalid_grant`.** The
  Google Cloud app was still in "Testing" status, where Google expires
  refresh tokens after 7 days. Fix: publish the app (production, no
  verification needed for personal use) and re-authorize once. Bucket:
  expensive (auth) — confirmed with user.
- **Publishing requires a public home page and privacy policy URL, so
  the repo goes public — as a NEW repo with a single fresh commit, not
  by flipping the old repo public.** Why: history before the Sept 15
  scrub contains real school/class names and a real Drive folder ID, and
  GitHub can keep serving rewritten-away commits by SHA, so rewriting
  history in place isn't reliable. Old repo is renamed and archived
  (kept private) rather than maintained in parallel. Bucket: expensive
  (public data) — confirmed with user.
- **Added PRIVACY.md** describing scopes (gmail.readonly on one label,
  drive.file), where data goes (Anthropic API, Slack), and what's stored
  (sent log only). Used as the OAuth consent screen's privacy policy
  link. Bucket: cheap.
- **OAuth app published to production.** Branding links: home page =
  public repo, privacy policy = PRIVACY.md on GitHub; `github.com`
  added as an authorized domain (Google requires the links' domain
  there); terms-of-service link left empty (optional). App stays
  unverified — owner sees Google's "unverified app" warning at sign-in,
  100-user lifetime cap. A pre-push hook in .git/hooks (local only)
  blocks pushing the old history to the public repo. Bucket: expensive
  (auth) — confirmed with user.
- **On GitHub Actions, the run log names emails by Gmail message ID, not
  subject; local runs still log subjects.** Why: a public repo's Actions
  logs are public, and subjects can name a school. Detected via the
  `GITHUB_ACTIONS` env var. Slack warnings still list real subjects
  (Slack is private). Residual risk: a traceback from a failed email
  could still echo email content in its exception message. User chose
  this over "never log subjects anywhere". Bucket: expensive (public
  data) — confirmed with user.
- **Skipped the ~2-week backlog from the outage** by moving the Drive
  sent log's `last_run` cursor from 2026-09-17T22:20 to
  2026-09-30T20:29 (UTC — matches the cloud runner's clock). Sent
  history (45 rows) untouched. Email that arrived during the outage
  will never be posted. Bucket: expensive (real data) — confirmed with
  user.
- **Local config.yaml gained `storage.drive_folder_id`**, set to the
  same folder the old code had hard-coded, so history carries over.
  Bucket: cheap.

## 2026-10-01

- **Sent-log migration: old single-`category` table is rebuilt into the
  two-flag layout automatically in `init_db()`.** Why: the Sept 15
  redesign changed the table, but `CREATE TABLE IF NOT EXISTS` never
  alters an existing one, so every `log_sent()` since then failed
  ("no column named requests_volunteer_help") — posts went out but were
  never recorded, so dedup forgot them. Mapping mirrors the old
  `decide()`: volunteer_ask → volunteer flag, fundraiser → promotional
  flag, schedule_change/deadline/classroom_update → neither. One
  transaction; a failure rolls back to the untouched old table. Done in
  code (not a one-off fix to the Drive file) so it's tested and also
  fixes anyone else's older sent log. Verified on a downloaded copy of
  the real log: 45 rows → 38 neither / 6 volunteer / 1 promotional,
  cursor preserved. Posts from Sept 15–17 and Sept 30 remain unrecorded
  (not backfilled — user's choice). Bucket: expensive (schema, real
  data) — confirmed with user.
- **Per-email failure warning in Slack now distinguishes "couldn't
  process" (never posted) from "posted but couldn't record it" (may
  repeat later).** Why: a sent-log write failing after a successful post
  produced a false "Couldn't process" alarm. Bucket: cheap — confirmed
  with user.
- **Out-of-office auto-replies are skipped, two layers.** (1) Code:
  `gmail_client._is_auto_reply()` drops any email with
  `Auto-Submitted: auto-replied` (RFC 3834) before the model sees it —
  free and deterministic. Deliberately NOT `auto-generated`, which bulk
  newsletter tools may put on real announcements. (2) Prompt backstop
  for servers that omit the header: return empty items and leave
  `is_reply_with_no_new_info` false — that flag posts a "nothing new"
  Slack notice, which nobody wants for an auto-reply. Reused the
  existing empty-items path instead of adding a new output field.
  Rejected: Gmail filter on subject wording (user tried it; brittle,
  misses non-English/odd phrasings, could hide "Ms. X out — sub info").
  Bucket: cheap — confirmed with user.

## 2026-10-05

- **Scheduled runs moved from :30 to :17 past the hour** (14:17 / 19:17
  / 23:17 UTC). Why: three labeled emails sat unposted because GitHub
  hadn't started the 14:30 run 6+ hours later; all week, runs had
  started 3–4 hours late. GitHub queues scheduled jobs and :00/:30 are
  its busiest minutes. Helps but doesn't guarantee — considered and
  deferred: a 4th buffer run, or an external trigger. Bucket: cheap —
  confirmed with user.
- **Cursor and Gmail query are now explicit UTC; query uses Unix
  seconds (`after:<epoch>`) instead of `after:YYYY/MM/DD`.** Why: Gmail
  reads a date as midnight in the account's time zone, but the cursor
  was naive UTC — after an evening run in a US time zone the UTC date
  had already rolled over, so the next query would skip anything
  arriving between that run and local midnight (none lost yet, checked).
  Also fixes local vs. GitHub (UTC) runs disagreeing about what a stored
  cursor means. Assumption: a stored cursor with no offset is read as
  UTC — every recent one was written by GitHub. `received_at` (the
  "Received:" time shown to the model) deliberately left as local
  time — separate question. Verified live: the timestamp query against
  the real inbox returned exactly the expected emails. Bucket: cheap —
  confirmed with user.

## 2026-10-06

- **Repeats are tagged "_Follow-up:_" in Slack instead of hidden.** Why:
  a field trip posted twice (evening chaperone schedule,
  then a morning reminder with bag lunch / sunscreen). Dedup already
  knew it was a repeat, but only promotional items ever used that fact;
  everything else is deliberately always-included. Tagging keeps the
  new details while making true repeats easy to skim. Applies to any
  included item whose dedup check says already-sent (including promos
  let through by the deadline window). Rejected: suppressing repeats —
  topic matching is a fuzzy heuristic (exact key or 2+ shared words,
  21-day lookback, same school), so a wrong match would hide a real
  email; and "suppress unless new info" needs a model judgment that
  would likely have dropped this exact reminder. Assumption: tag wording
  and position (leading italic `_Follow-up:_`). Bucket: cheap —
  confirmed with user.

## 2026-10-13

- **Email body falls back to the HTML part when the plain-text part is
  empty or a placeholder.** Why: one school bulk mailer ships
  `<!--placeholder-->` as its plain part and a billing system ships an
  empty one, so 7 of ~30 labeled emails last week reached the model as
  subject-only — including an urgent closure notice and sign-up
  emails, which lost their key details. The previous Zapier setup read these fine.
  Dry replay of all affected emails now produces full summaries; the
  billing emails also now get the school's name instead of a sender
  domain. Assumption: "placeholder" = fewer than 50 visible characters
  after removing HTML comments (real cases were 0 and 18); a short real
  reply crossing that line just reads its identical HTML version.
  HTML→text uses stdlib regex + `html.unescape` (drops style/script/
  head, keeps paragraph breaks) rather than adding BeautifulSoup. Not
  done: keeping link URLs from `<a href>` — changes what the model can
  see/repeat into Slack, separate decision. Bucket: cheap — confirmed
  with user.
- **Conversations the family is part of are skipped in code: any
  email where this account sent an earlier message in the same Gmail
  thread.** Why: user's call — staff answering the family's own
  question (lost item, meeting about their child) is a conversation
  they're already in, and the model's handling of these flip-flopped
  between "nothing new," "irrelevant," and a real summary on reruns of
  the same email. Uses Gmail's SENT label (no address to configure);
  only sent messages BEFORE this one count, so replying to a broadcast
  later doesn't hide it. Checked against 3 weeks of real labeled mail:
  skips exactly the 10 conversation emails, zero broadcasts or group
  threads. Rejected: recipient-count rules — the school's broadcast
  system addresses each family individually, so a newsletter looks
  like a 1-recipient email. Costs one extra Gmail call per new email.
  Bucket: cheap — confirmed with user.
- **Staff-initiated personal notes to just this family return nothing
  (prompt rule).** Why: same user decision; these can't be caught in
  code (family hasn't replied yet when the run sees them). Test is the
  audience, not the topic; when unclear, treat as a group message
  (missing an announcement is worse than posting one personal note).
  Replayed 5 real notes twice: the 4 personal ones skipped both times;
  a teacher-out notice to the whole class correctly still posted; 6
  group emails unaffected. Bucket: cheap — confirmed with user.
- **"Parent reply to X — nothing new" notices removed.** Why: user's
  call — pure noise (3 last week), and mislabeled when staff replied.
  The model's reply flag stays; it now only changes the run-log line.
  Bucket: cheap — confirmed with user.
- **Fuzzy dedup ignores generic words; short keys can match on fewer
  words.** Why: replaying the matcher over all 78 real sent-log rows
  found 5 outright wrong matches (two different field trips on
  "field"+"trip"; two different no-school days and an emergency closure
  matching a walk-to-school day on "school"+"day"+"2026") plus 4 right
  answers reached via a wrong partner. Wrong matches mislabel items as
  follow-ups AND can suppress a promotional item entirely. Now dropped
  before comparing: tokens with digits, month names, a small evidence-
  built generic list (school, day, field, trip, parent(s), update,
  weekly, the/and/for), and the family's school/class names from config
  (`Config.name_words()` — they're in half the keys). Plurals are
  folded ("tops"/"top"). Match needs 2 shared distinctive words, or all
  of them when a key has fewer than 2 left; a key with none left never
  fuzzy-matches. Replay result: all 5 wrong matches gone, the 4 lucky
  ones now match the right partner, one new (correct) match, one true
  repeat lost (a supplies email that added a photo request — low cost).
  Assumption: a fixed generic list, to be extended as new wrong matches
  show up. Rejected: deriving "common words" from log frequency — the
  true repeats break it (one field trip's name was in 5 keys because
  it was mentioned 5 times). Not done: giving the model recent topic keys to
  reuse — moves "same event?" from a checkable fact to model judgment.
  Exact-key matches unchanged, so weekly newsletters still get tagged
  (separate fix). Bucket: cheap — confirmed with user.
- **Weekly class recap gets a dated topic_key (prompt rule), e.g.
  "room12-class-update-2026-10-09".** Why: every weekly newsletter's
  recap reused one undated key, so each exact-matched the first and was
  tagged "Follow-up" despite all-new content. Chose a prompt rule over a
  new `is_class_recap` output field: no schema/model/decide changes, and
  the digit-dropping from the fuzzy-dedup fix means a dated recap key
  can't fuzzy-match last week's either. If the model ever omits the
  date, the cost is just the old mislabel. Replayed two real weekly
  updates twice each against the real sent log: recap dated and new
  every time; recurring calendar items in the same email still
  correctly tagged as follow-ups. Bucket: cheap — confirmed with user.
- **No sender-to-school mapping for the billing system (deferred).**
  Why: billing emails were labeled with a sender domain only because
  the model saw an empty body; after the HTML fallback fix, replay
  labels them with the school's name. Revisit only if it recurs.
  Bucket: cheap — flagged to user.
- **Revised: personal notes and family conversations are judged by
  "is there an action?", not "who is it addressed to?" — and the
  thread check is now a hint to the model, not a skip.** Supersedes
  the thread-skip and personal-note entries above. Why: user's call
  after walking through it — a personal note asking the family to send
  something in is worth a Slack line; general praise isn't. Same test
  for staff replies in threads the family wrote in: the code skip would
  have hidden a rescheduled meeting. The code still computes
  `family_in_thread` (SENT label, earlier messages only) and passes it
  as a line in the model's input. Prompt: for personal notes and
  flagged threads, extract only actions or plan changes; skip praise,
  check-ins, thanks, chit-chat, and anything only in the quoted
  earlier messages. The flag is explicitly "a hint, not a verdict":
  Gmail can thread separate same-subject broadcasts together, so a
  class-wide message with the flag is extracted as usual — the old
  skip would have hidden every later newsletter after one reply.
  Tie-breaker: when unclear, extract. Replayed ~20 real emails up to 3
  times: praise/check-ins skipped every time, every action and plan
  change posted every time, group emails unaffected. Bucket: cheap —
  confirmed with user.
- **Hard prompt rule: never copy passwords, login codes, PINs, account
  numbers, usernames, door codes into a summary — point to the email.**
  Why: the action-only replay posted a shared login's
  username AND password into the would-be Slack text, on both runs.
  After the rule: clean on 5 of 5 runs. Bucket: cheap — flagged to user
  (prompt rule; a model could still slip — see note in chat).
- **Thread lookup failures are caught and treated as "not in a
  thread."** Why: a transient Gmail 500 on the new threads.get call
  crashed a replay; in the pipeline it runs during the fetch, before
  the per-email safety net, so it would have failed the whole run.
  False is the safe side (normal rules apply). Bucket: cheap.
- **Code backstop for credentials: a bullet that looks like it holds a
  password/PIN/username/access code is replaced with a pointer to the
  email.** Why: the prompt rule alone is a model instruction; in
  testing the model once wrote a shared login's username and password
  into a summary. `decide()` checks each summary with a regex (a
  credential word followed by a 4+ character value-shaped token, minus
  common harmless follow-ons like "reset"/"details"). Assumption: hold
  back the WHOLE bullet rather than redact the value — a wrong guess
  at where a secret ends would leak part of it; erring costs one
  "check the email directly" line. Other bullets from the same email
  still post. The held-back item is written to the sent log (Drive)
  with a placeholder summary, and the run log gets a warning (message
  ID only). Checked against all 78 real posted summaries: 0 false
  positives. Bucket: cheap — confirmed with user.
- **Runs every 30 minutes (:17 and :47 UTC), and only one run at a
  time.** Why: user wanted fresher digests; measured cost is per email
  (~8.5–9.5K input tokens each, ≈$0.04 with output), not per run — an
  empty run makes no Claude call and Actions minutes are free for a
  public repo, so frequency is nearly free. The workflow gets a
  `concurrency:` group (cancel-in-progress false): without it, a
  late-starting run overlapping the next one would read the same
  cursor, double-post, and the last sent-log upload would erase the
  other's records. Assumption: :17/:47 rather than literal `*/30`,
  which lands on GitHub's busiest minutes (see 2026-10-05). Doesn't fix
  GitHub's best-effort start times — runs can still be late or skipped;
  real-time would need an external trigger (not done). The guard
  doesn't cover a local schedule (none found on this Mac). Bucket:
  cheap — confirmed with user.
- **Drop the added date when the summary already says "today" /
  "tomorrow" and that's true.** Why: a summary saying an event was
  "today" also got the date appended, so it said the day twice. The prompt allows
  relative words, so this is fixed in `_format_bullet` next to the
  existing "date already in the summary" check. Covers today / tonight /
  this morning / this afternoon / this evening (event is today) and
  tomorrow (event is tomorrow). Assumption: only drop the date when the
  word is still accurate when the bullet is built — if an email sat
  overnight, "today" is stale and the real date stays as the tell.
  Bucket: cheap.
- **One announcement with several parts becomes one item.** Why: a
  fundraising email came out as two bullets (the campaign's end date;
  a kickoff today) that both repeated the campaign's name. New prompt section in
  `extract_system.md`. Assumptions: (1) the combined item's
  deadline_date is the *soonest* date the family acts on/attends, so it
  sorts first and isn't held back by the promotional timing rule; later
  dates go into the sentence. (2) topic_key is named after the program
  itself (e.g. `annual-fund-2026-27`), so a later reminder about any
  part posts as a Follow-up rather than looking brand new. (3) Narrow:
  unrelated events next to each other in a newsletter stay separate.
  Tradeoff accepted: a later reminder about just one part gets a
  "Follow-up" tag even if that part is new to you. Added eval fixture
  ANNUAL_GIVING_KICKOFF. Bucket: cheap (prompt text) — user chose
  combine over keep-separate.

## 2026-10-15

- **Digest moved to a different Slack channel.** Why:
  user asked to move the digest to a different channel. Changed in local
  `config.yaml` (gitignored). The scheduled GitHub Actions run reads its
  config from the `SCHOOL_DIGEST_CONFIG_YAML_B64` secret, so that secret
  also has to be re-encoded and updated, or the scheduled runs keep
  posting to the old channel. The Slack app has to be invited to the new
  channel before it can post there. Bucket: cheap (one config value).
- **Share the project as a GitHub template repo for technical friends,
  not as a Claude skill.** Why: it's a running program (secrets, a
  schedule, a SQLite sent log), not a set of instructions; a skill could
  later guide setup but can't be the product. Bucket: cheap.
- **Scheduled runs are off until the repo variable `DIGEST_ENABLED` is
  `true`; manual runs always go.** Why: a copy made from a template
  starts its cron schedule immediately and would fail every 30 minutes
  before setup is done. The original repo needs the variable set too,
  before this change is pushed, or its digest silently stops.
  Bucket: expensive-ish (touches the live schedule), mitigated by
  setting the variable first.
- **Renamed three distinctive event/place names in the test fixtures
  and one prompt example to generic ones.** Why: the fixtures came from
  real emails, and those names could let someone who knows the schools
  recognize them. Common school phrases were left alone. Unit tests
  pass; the paid live eval wasn't re-run. Bucket: cheap.
- **Decision log moved from the repo root to `docs/`, with a note
  that it's the original author's history.** Why: people using the
  template don't need it to set up, and the root stays focused on
  setup files. Bucket: cheap.
- **Decision log moved back to the repo root, after a privacy pass.**
  Supersedes the move to `docs/` above. Why: user's call — the log
  belongs at the root, but first it was scrubbed: real quotes from
  school staff, a real closure and meeting, the family's time zone, and
  a real fundraising event's venue and dates were reworded generically.
  The same event's venue and dates were also in the extraction
  prompt's worked example and a test docstring; both now use a made-up
  "Annual Fund" event that doesn't match any fixture. Earlier versions
  of this file are still in the public repo's history. Bucket: cheap
  (wording only), except the public history question — flagged to user.
- **Republished as a new public repo with one fresh commit, after a
  full privacy pass over every tracked file.** Supersedes the "earlier
  versions are still in history" note above. Why: user's call — the
  public history held real event details, quotes and a real school
  calendar. All fixture dates, times, dollar figures, program and class
  names, staff names, vendors, building details and the example
  family's grades were replaced with made-up ones (tests updated to
  match); LICENSE names the GitHub account instead of a person. The old
  repo was renamed `school-email-digest-private`, made private, and its
  schedule turned off; the new repo keeps the old name so the Google
  OAuth home-page and privacy-policy links still work. The live digest
  now runs from the new repo (free Actions minutes for public repos);
  its four secrets were re-added by hand. Paid live eval not re-run
  after the fixture rewrite. Bucket: expensive (public data, auth
  links, live schedule) — confirmed with user.
- **Docs tell private copies to run every 2 hours; the shipped schedule
  stays every 30 minutes.** Why: the original repo is public (free
  Actions minutes), but template copies are private: 2,000 free
  minutes a month, each run billed as a full minute, so every 30
  minutes is ~1,500 — under the cap but close, and runs stop if it's
  exceeded. Note added to README Part 2 step 7 and the workflow
  comment rather than switching automatically. Assumption: every 2
  hours (`'17 */2 * * *'`, ~370 minutes a month) as the recommended
  private-repo schedule. Bucket: cheap (docs only).
