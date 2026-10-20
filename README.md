# School Email Digest

Reads labeled school emails from Gmail, figures out what's actually new
and relevant, and posts a triaged summary to Slack — without repeating
itself and without needing you to babysit it.

Built to replace a Zapier + Claude pipeline that had no memory across
runs (so it guessed at what counted as "already mentioned") and asked
one small model to force every email — single-topic note or 15-item
newsletter alike — into one category. This version pulls a *list* of
relevant items out of each email, checks each one against a real dedup
log, and applies the inclusion rules in plain Python — so a mostly-
irrelevant newsletter with one real match buried in it doesn't lose
that match, and nothing is guessing at something it could instead check
or compute.

## How it works

```
Gmail (labeled emails since last run)
        │
        ▼
  extract_email()          — the only Claude call. Reads the whole email
        │                     (single note or long newsletter) and pulls
        │                     out a LIST of relevant items — zero, one,
        │                     or many — each with a deadline, a topic_key,
        │                     and two flags (is this asking a parent to
        │                     volunteer, is this the kind of thing that
        │                     shouldn't repeat every mention).
        │                     Content about other grades or pure
        │                     marketing noise never becomes an item at
        │                     all.
        ▼
  check_dedup()  (per item)  — SQLite lookup, not a guess
        │  → already sent? when?
        ▼
  decide()                    — pure Python, no LLM call. Two
        │                        independent flags — is this a volunteer
        │                        ask (only kept if it isn't aimed at some
        │                        other class), is this promotional (only
        │                        kept near its deadline or when new) —
        │                        are all inclusion ever depends on;
        │                        everything else survives by default.
        │                        Anything already sent recently is
        │                        tagged "Follow-up:" rather than hidden.
        │                        Deterministic once each item carries
        │                        real facts — fully unit-tested without
        │                        touching the network.
        ▼
  post_message()  +  log_sent() (per included item) — Slack, and the
                                  sent-log for next time
```

One Claude call, one lookup per item, one deterministic decision step.
The second model call from the earlier version is gone — once the data
has real structure, applying the rules to it stopped being a judgment
call. See `prompts/extract_system.md` for the full extraction
methodology.

## Choose how you'll run it

There are two ways to run this. Everyone starts with **Part 1**; **Part 2**
is optional. If you do Part 2, **Part 3** (~15 more minutes) makes it
run within minutes of a school email arriving instead of on a timer.

| | **Local-only** (Part 1) | **Cloud** (Part 1 + Part 2) |
|---|---|---|
| Runs on | Your own computer | GitHub Actions (free for this usage) |
| Runs when your laptop is closed | No | Yes |
| Sent log (what's already been posted) | A file on your computer | A file in a Google Drive folder, shared by every run |
| Extra accounts beyond Part 1 | None | GitHub, Google Drive |
| Setup time | ~45 minutes | ~30 more minutes |

You can also do both at once — a cloud schedule plus occasional local
runs — because Drive keeps them on one shared history. See
[Known limitations](#known-limitations) before scheduling both, though.

## Part 1: Local setup

You'll need: a computer with **Python 3.9 or newer** (`python3 --version`
to check), the Gmail account that receives school email, a Slack
workspace where you're allowed to add an app, and a credit card for the
Anthropic API (typical cost is a few cents a day on the default model).

### 1. Get the code and install dependencies

Make your own copy first. On this repository's GitHub page, click
**Use this template** → **Create a new repository** → any name →
**Private** → **Create repository**. Unlike a fork, your copy starts
with its own clean history and can be private (see [Privacy](#privacy)
for why that matters). Then clone *your* copy:

```bash
git clone https://github.com/<you>/<your-repo>.git school-email-digest
```

```bash
cd school-email-digest
```

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

The `venv` step creates a private Python environment in `.venv/` so
these packages don't interfere with anything else on your computer. Run
`source .venv/bin/activate` again whenever you open a new terminal to
work on this (on Windows: `.venv\Scripts\activate`).

> Your copy's scheduled cloud runs stay off until you switch them on in
> Part 2, so it won't fail on every run while you set things up.

### 2. Anthropic API key

1. Sign in at [console.anthropic.com](https://console.anthropic.com),
   add billing, and open **API Keys** → **Create Key**.
2. Copy the key (starts with `sk-ant-`). You'll paste it in step 4.

### 3. Slack app

1. Go to [api.slack.com/apps](https://api.slack.com/apps) →
   **Create New App** → **From scratch**. Name it anything (e.g.
   "School Digest") and pick your workspace.
2. In the left sidebar, **OAuth & Permissions** → **Bot Token Scopes** →
   add `chat:write` (to post messages).
3. Scroll up, click **Install to Workspace**, and approve.
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`).
5. In Slack, create the channel you want digests in (e.g.
   `#school-updates`), open it, and type `/invite @School Digest` (your
   app's name). The bot can only post to channels it's been invited to.
6. Get the channel's **ID**: click the channel name at the top of the
   channel, and look at the bottom of the **About** tab. It starts with
   `C` (e.g. `C0123456789`) and has a copy button. This goes in your
   config in step 7.

You can put a `#channel-name` in the config instead of the ID, but then
the app needs two more Bot Token Scopes to look the name up:
`channels:read`, plus `groups:read` if the channel is private.

### 4. Secrets file

```bash
cp .env.example .env
```

Open `.env` and fill in `ANTHROPIC_API_KEY` and `SLACK_BOT_TOKEN`. This
file is gitignored — it never gets committed.

### 5. Google Cloud project and credentials

This is the fiddliest step. It gives the tool permission to read your
Gmail (and, for Part 2, to save one file in Drive). Google's console
layout changes occasionally; if a menu name doesn't match exactly, look
for the closest equivalent.

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
   and create a new project (top bar → project picker → **New Project**).
   Any name works.
2. **APIs & Services** → **Library** → search for **Gmail API** →
   **Enable**. If you might do Part 2 later, also enable
   **Google Drive API** now.
3. Set up the consent screen: **APIs & Services** → **OAuth consent
   screen** (newer consoles call this **Google Auth Platform**).
   - User type: **External**.
   - App name: anything. Support and developer contact email: your own.
   - Under **Audience** / **Test users**, add the Gmail address that
     receives school email.
4. **Publish the app** (same page, under **Audience** or
   **Publishing status** → **Publish app** → confirm). This matters:
   while an app is in "Testing" status, Google expires its login after
   **7 days**, so the tool would stop working every week. You do *not*
   need Google's verification for personal use — publishing just means
   you'll see a "Google hasn't verified this app" warning when you
   authorize in step 8. That warning is expected for an app you made
   yourself; click **Advanced** → **Go to (your app name)**.
5. **APIs & Services** → **Credentials** (or **Clients**) →
   **Create Credentials** → **OAuth client ID** → Application type
   **Desktop app** → **Create**.
6. Click **Download JSON** and save the file as `credentials.json` in
   the project folder (next to `run.py`). Gitignored; never commit it.

The tool asks Google for exactly two permissions: **read-only** Gmail
access, and Drive access limited to **files this app itself creates**
(it can't see anything else in your Drive). It asks for the Drive one
even in a local-only setup, so switching to Part 2 later doesn't require
re-authorizing.

### 6. Gmail label and filter

The tool only ever reads emails with one specific Gmail label.

1. In Gmail, create a label — use a **single word with no spaces or
   slashes**, e.g. `School`.
2. Create a filter (search bar → the filter icon) matching your schools'
   senders, e.g. `from:(@example-elementary.org OR @example-preschool.org)`
   → **Create filter** → **Apply the label** → `School`. Tick **Also
   apply filter to matching conversations** to label existing mail.

Be generous with the filter — anything unlabeled is invisible to this
tool.

### 7. Config file

This file holds everything specific to your family: schools, classes,
Slack channel, Gmail label. Nothing else in the codebase should need
editing. Two ways to make it:

**Easiest: use the config builder.** Open `tools/config-builder.html` in
your web browser (double-click it in Finder / File Explorer). Answer the
questions, click **Download config.yaml**, and move the downloaded file
into the project folder. Check that it's named exactly `config.yaml`.
The page works offline, and nothing you type is sent anywhere.

**Or by hand:**

```bash
cp config.example.yaml config.yaml
```

Then open `config.yaml` and fill it in. Every setting is explained in
comments. For Part 1, leave `storage.drive_folder_id` as `""`
(local-only).

### 8. First run (dry run)

```bash
python run.py --dry-run --since-days 7
```

The first time, a browser window opens asking you to sign in to Google
and approve access (expect the "unverified app" warning from step 5).
After you approve, a `token.json` file is saved so you won't be asked
again. Gitignored; never commit it.

`--dry-run` prints what *would* be posted and touches nothing — no Slack
message, no sent-log update. (It does make real Anthropic API calls.)
`--since-days 7` looks back a week so there's something to see.

If the output looks right:

```bash
python run.py
```

That posts to Slack for real and records what was sent.

### 9. Schedule it (optional)

`run.py` doesn't need to stay running — each run picks up where the last
one left off. To run it automatically, use your computer's scheduler.
On macOS or Linux, `crontab -e` and add a line like this (7:30am,
12:30pm, 4:30pm daily — replace the path with your own):

```
30 7,12,16 * * * cd /full/path/to/school-email-digest && .venv/bin/python run.py >> data/run.log 2>&1
```

Your computer has to be awake at those times. If that's a problem,
that's what Part 2 is for.

## Part 2: Cloud setup (GitHub Actions + Google Drive)

This runs the digest on GitHub's servers on a schedule, so it works when
your computer is off. Because a cloud runner starts with a blank disk
every time, the sent log is kept in a Google Drive folder instead:
downloaded at the start of each run, uploaded at the end.

**Finish Part 1 first** — you need a working `token.json`, which can only
be created by the browser sign-in on your own computer.

### 1. Enable the Drive API

If you didn't in Part 1: in the same Google Cloud project, **APIs &
Services** → **Library** → **Google Drive API** → **Enable**.

### 2. Make sure your token covers Drive

A `token.json` created by this version of the tool already includes the
Drive permission. If yours came from an older version that only asked
for Gmail — or if a run later fails with a Drive "insufficient
permissions" (403) error — re-authorize to get a token covering both:

```bash
rm token.json
```

```bash
python run.py --dry-run
```

and approve in the browser again.

### 3. Create the Drive folder

1. In Google Drive, create a folder, e.g. `School Email Digest`.
2. Open it. The URL looks like
   `https://drive.google.com/drive/folders/1AbCdEf...` — copy everything
   after `/folders/`. That's the folder ID.
3. In `config.yaml`, set `storage.drive_folder_id` to that ID (in quotes).
   Or re-run the config builder, choose **Synced through Google Drive**,
   and paste the whole folder URL; it pulls out the ID for you.

Don't put any files in the folder yourself. The tool's Drive permission
only lets it see files it created, so it creates the sent-log file on
its first real run.

### 4. Seed Drive from your computer

```bash
python run.py
```

Afterwards, a file named `school-email-digest-sent-log.db` should appear
in the folder. If you'd already been running locally, your existing
history is uploaded, so nothing gets re-posted.

### 5. Put the code in a private GitHub repository

If you made your copy with **Use this template** in Part 1, it's already
a private repository. Skip to step 6.

Otherwise (see [Privacy](#privacy) for why this should be **private**):

1. On GitHub, **New repository** → any name → **Private** → don't add a
   README or license → **Create repository**.
2. Point your local copy at it and push (GitHub shows these commands on
   the new repo's page):

```bash
git remote set-url origin https://github.com/<you>/<repo>.git
```

```bash
git push -u origin main
```

### 6. Add four GitHub secrets

A GitHub Actions runner has none of your local files — no `.env`,
`config.yaml`, or `token.json`. You give it those as encrypted
**secrets**, which the workflow turns back into files at the start of
each run. In your repo: **Settings** → **Secrets and variables** →
**Actions** → **New repository secret**. Names must match exactly:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your `sk-ant-...` key, pasted as-is |
| `SLACK_BOT_TOKEN` | Your `xoxb-...` token, pasted as-is |
| `GMAIL_TOKEN_JSON_B64` | `token.json`, base64-encoded (below) |
| `SCHOOL_DIGEST_CONFIG_YAML_B64` | `config.yaml`, base64-encoded (below) |

**Base64-encoding** turns a whole file into one long line of letters and
numbers. The files are encoded because pasting raw multi-line JSON or
YAML into a secret tends to get mangled by quotes and special
characters when the workflow writes it back out; base64 has none. To
copy a file's encoded form to your clipboard:

macOS:
```bash
base64 -i token.json | pbcopy
```

Linux (then copy the output):
```bash
base64 -w 0 token.json
```

Windows PowerShell:
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("token.json")) | Set-Clipboard
```

Paste as the `GMAIL_TOKEN_JSON_B64` secret, then repeat with
`config.yaml` for `SCHOOL_DIGEST_CONFIG_YAML_B64`.

**Whenever you edit `config.yaml` later, re-encode it and update that
secret** — the cloud copy doesn't update itself.

`credentials.json` isn't needed in the cloud: `token.json` carries what's
required to keep access fresh. If Google ever revokes the token (e.g.
you change your Google password, or remove the app's access), cloud runs
fail until you repeat step 2 locally and update `GMAIL_TOKEN_JSON_B64`.

### 7. Review the workflow schedule

The workflow is `.github/workflows/run-digest.yml`. On each run, it:
checks out the code, installs Python and the dependencies, decodes the
two base64 secrets back into `token.json` and `config.yaml`, then runs
`python run.py` with the other two secrets as environment variables.

The schedule is set by the `cron:` line, **in UTC**. As shipped, it runs
every 6 hours (at :17 past 00, 06, 12 and 18 UTC). That's a *backstop*:
it assumes you'll also set up [Part 3](#part-3-run-when-email-arrives),
which starts a run within minutes of each school email, and the schedule
just catches anything Part 3 misses. To change it, edit that line (the
comments in the file explain the format), then commit and push. Keep
the minute off :00 and :30 — GitHub starts scheduled runs when it has
spare capacity, and those minutes are its busiest, so runs there can
start hours late or get skipped.

**Skipping Part 3? Run more often.** Every 6 hours alone means a digest
can arrive hours after the email. Without Part 3, run every couple of
hours instead:

```yaml
    - cron: '17 */2 * * *'
```

or a few fixed times a day, e.g. `'17 14 * * *'` for 7:17am US Pacific
daylight time. Don't go much more often than every 2 hours on a
*private* repo — which your copy should be (see [Privacy](#privacy)).
Private repos get 2,000 free GitHub Actions minutes a month, shared
across all your private repos, and GitHub rounds every run up to a
full minute even though this one takes about 30 seconds: every 2 hours
is about 370 minutes a month, every 30 minutes about 1,500 — close to
the limit, and runs stop for the rest of the month if you go over.
Claude cost barely depends on any of this: a run with no new email
makes no Claude call, and fewer runs just means each one catches up on
a bit more email.

The workflow also allows only one run at a time (its `concurrency:`
block), so a late run and the next scheduled one can't overlap and
post the same emails twice. That guard only covers GitHub runs — it
doesn't know about a local schedule on your own computer.

### 8. Turn it on and test

1. In your repo, open the **Actions** tab. If GitHub asks, click to
   enable workflows.
2. Select **School Email Digest** → **Run workflow** → **Run workflow**.
   This runs it once immediately rather than waiting for the schedule.
3. Click into the run to watch its log. A green check means it worked;
   check Slack and the Drive folder's file modified time.
4. Switch on the schedule: **Settings** → **Secrets and variables** →
   **Actions** → **Variables** tab → **New repository variable**, name
   `DIGEST_ENABLED`, value `true`. Until this exists, scheduled runs
   show as *skipped* (manual runs like step 2 always go). Delete the
   variable or set it to anything else to pause the digest.

After that it runs on schedule. GitHub emails you if a run fails.
Scheduled runs can start several minutes late when GitHub is busy.
Now do Part 3 so it runs when email arrives — or, if you're skipping
it, make the schedule more frequent as described in step 7.

## Part 3: Run when email arrives

GitHub can't see your Gmail, so on its own it can only run on a timer.
This part adds a small script that runs inside your own Google account
([Google Apps Script](https://script.google.com) — free, built into
every Google account). Every 5 minutes it checks for a new email with
your label, and if there is one, it asks GitHub to start the digest
right away. A run started this way begins within seconds, unlike
scheduled runs, which GitHub can start hours late.

The script only reads the time each labeled email arrived — never the
subject, sender or content — and its Gmail permission is read-only. The
digest itself still runs in GitHub exactly as before, and catches up on
everything since its last run, so a missed check costs nothing: the
next one, or the 6-hour backstop schedule, picks it up.

**Made your copy before this part existed?** Template copies don't
update themselves. Update `.github/workflows/run-digest.yml` in your
repo to the current version and push it *before* step 3 — the script
labels its runs in a way older workflow files reject (HTTP 422). The
current file also drops the schedule to a 6-hour backstop, so finish
this part promptly after pushing.

### 1. Make a GitHub token that can only start this workflow

1. On GitHub: your profile picture → **Settings** → **Developer
   settings** → **Personal access tokens** → **Fine-grained tokens** →
   **Generate new token**.
2. Name it e.g. `school digest trigger`. Pick an **expiration** and put
   a reminder in your calendar for that date (see step 4).
3. **Repository access** → **Only select repositories** → your digest
   repo.
4. **Permissions** → **Repository permissions** → **Actions** → **Read
   and write**. Leave everything else as is. (*Read and write* on
   Actions lets the token start, cancel and delete workflow runs on
   this one repo; it can't read or change your code or secrets.)
5. **Generate token** and copy it (starts with `github_pat_`). You
   won't be able to see it again.

### 2. Create the script

Sign in to Google as the Gmail account that receives the school email,
then:

1. Go to [script.google.com](https://script.google.com) → **New
   project**. Rename it (top left) to e.g. `School digest trigger`.
2. Delete what's in `Code.gs` and paste in the contents of
   [`tools/gmail-trigger.gs`](tools/gmail-trigger.gs). Edit the three
   lines near the top:
   - `GITHUB_REPO` — your repo as `owner/name`, e.g.
     `your-github-name/school-email-digest`
   - `GMAIL_LABEL` — the same label as `gmail: label:` in your
     `config.yaml`
   - `CHECK_EVERY_MINUTES` — leave at 5 unless you have a reason
3. Replace the script's settings file. This turns on the Gmail API for
   the script and limits it to read-only Gmail access, outside requests
   (to call GitHub), and managing its own timer.
   1. In the narrow icon bar on the far left, click the **gear**
      (**Project Settings**) and tick **Show "appsscript.json" manifest
      file in editor**.
   2. Click the **`< >`** icon (**Editor**). The **Files** list next to
      it now shows `appsscript.json` under `Code.gs`. Click it.
   3. Click in the text, select all (⌘A / Ctrl+A), and paste the
      contents of
      [`tools/gmail-trigger.appsscript.json`](tools/gmail-trigger.appsscript.json)
      over it.
   4. Save (⌘S / Ctrl+S). Check that **Services**, below the Files
      list, now shows **Gmail**. If it doesn't, the file didn't save —
      try again.
4. **Project Settings** → **Script Properties** → **Add script
   property**: name `GITHUB_TOKEN`, value the token from step 1 →
   **Save script properties**. (Keeping it here rather than in the code
   means the code can be copied or shared without leaking it.)

### 3. Start it

1. In the **Editor**, pick `installTrigger` in the function dropdown
   in the toolbar and click **Run**.
2. Google asks you to authorize the script. Because it's your own
   unpublished script, it shows **Google hasn't verified this app** →
   **Advanced** → **Go to School digest trigger (unsafe)** → **Allow**.
   Check the list says Gmail access is *view* only.
3. The log at the bottom should finish without errors. If you have a
   labeled email from the last two days, GitHub's **Actions** tab now
   shows a run (it may be marked *skipped* if `DIGEST_ENABLED` isn't
   set yet — see Part 2 step 8).
4. To confirm the timer exists: **Triggers** (clock icon, left) shows
   `checkForNewEmail`, time-based, every 5 minutes.

To test end to end, send yourself an email that your filter labels and
watch the Actions tab: a run should appear within about 5 minutes.

**If the log shows an error:**
- `Gmail is not defined` — the settings file from step 2.3 wasn't
  saved. Redo it, check **Services** shows **Gmail**, and run
  `installTrigger` again (Google asks for permission again, now
  including read-only Gmail).
- `GitHub refused to start the workflow (HTTP 422)` with `Unexpected
  inputs provided` — the workflow file in your GitHub repo predates
  this trigger. See the note at the top of this part.
- `HTTP 401` or `403` — the token is wrong, expired, or missing the
  Actions permission (step 1).

### 4. Keeping it running

- **When the token expires**, the script's checks start failing and
  Google emails you a failure summary (from Apps Script, usually once a
  day). Make a new token as in step 1 and paste it over `GITHUB_TOKEN`
  in Script Properties. Until then the backstop schedule keeps the
  digest going, just less often.
- **To pause the digest**, delete or change the `DIGEST_ENABLED`
  variable as in Part 2 step 8 — runs this script starts respect it too.
  **To stop the script itself**, run `removeTrigger` the same way you
  ran `installTrigger`.
- **If you change your label**, update `GMAIL_LABEL` in the script as
  well as `config.yaml`.

## Running it

```
python run.py                           # real run: posts to Slack, updates the sent log
python run.py --dry-run                 # prints what would be posted, touches nothing
python run.py --dry-run --since-days 7  # look further back than the last run
```

Avoid `--since-days` *without* `--dry-run`: most items are always
included regardless of whether they were sent before, so re-processing
old email re-posts them.

## Testing

Two different things, deliberately kept separate:

- **`pytest`** — fast unit tests for everything that doesn't need a live
  API call: the inclusion rules in `decide()`, the dedup logic (exact
  match, reworded-topic fuzzy match, lookback window, cross-school
  isolation), config loading, prompt rendering, the Drive sync and
  local-only storage paths, Slack channel lookup, and the extraction
  retry. Runs in a couple of seconds, no API keys needed.

- **`python eval_live.py`** — the actual eval harness. Runs the sample
  emails in `tests/fixtures/sample_emails.py` through the real
  extract/decide pipeline against the live API and checks that the
  right content survived — as substrings that must (or must not) appear
  in the final Slack text, since one email can produce several items at
  once. This costs real API calls and needs `ANTHROPIC_API_KEY` set. Run
  it after any prompt change — that's how you catch a regression before
  it shows up as a wrong Slack message instead of a red test.

The default fixture set (paired with `config.example.yaml`) covers the
original single-topic failure modes (a genuine deadline, a reply-all
with nothing new, an out-of-scope grade, a volunteer ask that should and
shouldn't count) plus newsletter-shaped cases modeled on real emails
that broke the original one-item design — a long, mostly-irrelevant
newsletter with exactly one real match buried inside it.

A second, independent set simulates a completely different family
(four schools, grades K–9) to check the design generalizes beyond the
setup it was tuned on:

```bash
python eval_live.py --config config.friend-test.yaml --fixtures tests.fixtures.friend_test_emails
```

Add to either set as real emails surface new edge cases — that's the
whole point of owning the eval set yourself instead of just trusting
the prompt. If you base a fixture on a real email, genericize it first:
school, class, teacher, program, and campaign names, sender addresses,
and anything else specific enough to identify a real school or family.

## Privacy

This tool handles your children's school email, so it's worth knowing
exactly where that goes:

- **Email content** is sent to the Anthropic API for extraction.
- **Summaries** are posted to your Slack channel.
- **The sent log** (short topic labels and one-line summaries) stays on
  your computer, or goes to your Google Drive folder if you set one.
- **The Gmail trigger** (Part 3), if you use it, runs in your own Google
  account and reads only when labeled emails arrived. It sends GitHub
  nothing but "start a run."
- **Run logs** include email subject lines. Locally that's just your
  terminal or log file — but in GitHub Actions they're in the run log on
  GitHub.

That last point is why **the repo you run GitHub Actions from should be
private.** Actions logs in a public repository are visible to anyone.
A GitHub *fork* of a public repository is always public and can't be
made private, so use **Use this template** (Part 1 step 1) rather than
clicking Fork.

Never commit `.env`, `config.yaml`, `credentials.json`, `token.json`, or
anything in `data/` — all are already in `.gitignore`.

## Known limitations

- **Not instant.** With Part 3, a digest posts a few minutes after a
  school email arrives (up to 5 minutes for the check, about a minute
  for GitHub to start, and the run itself). Without it, it depends on
  your schedule.
- **Only labeled email.** Anything your Gmail filter misses is invisible.
- **Daylight saving time.** Neither cron nor GitHub Actions schedules
  shift automatically when clocks change; update the times if it matters.
- **Local and cloud runs together.** Each run records "last checked at"
  using its own machine's clock, and GitHub's runners use UTC. If you
  run both local and cloud schedules and your computer isn't on UTC,
  the two can disagree about where the last run left off, so emails can
  be missed or repeated. Pick one schedule unless you've confirmed this
  isn't an issue for you. Also avoid scheduling them at overlapping
  times: two simultaneous runs each upload their own copy of the sent
  log, and the last one to finish wins.

## License

MIT — see [LICENSE](LICENSE).
