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
