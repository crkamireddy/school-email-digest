# Decision log

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
  in the "fictional" sample set.** Specific dollar figures and generic
  program names (e.g. teacher-treat and board-game volunteer programs)
  were left as-is. Bucket: cheap.
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
  was naive UTC — after an evening Pacific run the UTC date had already
  rolled over, so the next query would skip anything arriving between
  that run and Pacific midnight (none lost yet, checked). Also fixes
  Mac (Pacific) vs. GitHub (UTC) runs disagreeing about what a stored
  cursor means. Assumption: a stored cursor with no offset is read as
  UTC — every recent one was written by GitHub. `received_at` (the
  "Received:" time shown to the model) deliberately left as local
  time — separate question. Verified live: the timestamp query against
  the real inbox returned exactly the expected emails. Bucket: cheap —
  confirmed with user.
