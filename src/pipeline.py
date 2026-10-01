"""Ties the stages together. Each run: fetch anything new since last run,
extract a list of candidate items per email, check the real dedup log
per item, decide (pure Python) what survives, post what's left as one
combined message per email, log what was actually sent. No stage guesses
at something another stage can know for a fact.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

from anthropic import Anthropic

from . import dedup_store
from . import drive_state
from .config import Config, load_config
from .decide import decide
from .extract import extract_email
from .gmail_client import fetch_labeled_emails
from .models import DedupStatus
from .slack_client import post_message

log = logging.getLogger("school_email_digest")


def _log_name(email) -> str:
    """How an email is named in the run log. On GitHub Actions the log of
    a public repo is public too, so use the opaque Gmail message ID — a
    subject line like a school newsletter's title would identify the
    school. Locally the log stays on your own machine, so the subject is
    fine and far easier to read. Find a logged ID in Gmail at
    https://mail.google.com/mail/u/0/#all/<id>."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return f"message {email.message_id}"
    return repr(email.subject)


def _failure_notice(failed_subjects: list[str], unrecorded_subjects: list[str]) -> str:
    """The Slack warning for a run where some emails went wrong. Two
    different situations, worded differently so the warning is never a
    false alarm: an email that never got posted (go read it yourself),
    vs. one that DID get posted but couldn't be recorded (nothing to do
    now — but a later reminder about it may come through as if new)."""
    parts = []
    if failed_subjects:
        parts.append(
            f"⚠️ Couldn't process {len(failed_subjects)} email(s) this run — "
            "worth checking these directly:\n"
            + "\n".join(f"• {s}" for s in failed_subjects)
        )
    if unrecorded_subjects:
        parts.append(
            f"⚠️ Posted {len(unrecorded_subjects)} email(s) above but couldn't record "
            "them as sent — nothing to do now, but a later reminder about these may "
            "get posted again as if new:\n"
            + "\n".join(f"• {s}" for s in unrecorded_subjects)
        )
    return "\n\n".join(parts)


def run(config: Config | None = None, dry_run: bool = False, since_days: int | None = None) -> list[str]:
    """Runs one full pass. Returns the list of Slack messages that were
    (or, in dry_run, would have been) posted — handy for tests and for
    eyeballing a run before trusting it with real Slack access.

    since_days overrides the stored cursor to look back further —
    useful for exploring more of your inbox without waiting for new
    email to arrive. Pair it with dry_run=True unless you actually want
    to re-post: items with neither flag set (schedule changes, deadlines,
    classroom updates, most news) are deliberately always-included
    regardless of dedup status, so a real (non-dry) re-run over
    already-processed email will re-post them.

    When config.drive_folder_id is set, the dedup database lives in
    Drive, not just on whatever machine happens to run this — downloaded
    fresh at the start of every real run and uploaded back at the end.
    That's what lets a local schedule and a cloud schedule share one
    dedup history instead of silently diverging into two. Without it,
    the local SQLite file is the only copy (fine for a single machine).
    Dry runs skip Drive entirely, same as they skip every other
    persistent side effect."""
    config = config or load_config()
    client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    sync_with_drive = not dry_run and config.drive_folder_id is not None
    if not dry_run and not sync_with_drive and os.environ.get("GITHUB_ACTIONS") == "true":
        # A cloud runner starts from a blank disk every time, so a
        # local-only sent log would be empty on every run — no cursor,
        # no dedup history, the same email re-posted over and over.
        raise RuntimeError(
            "Running on GitHub Actions without storage.drive_folder_id set. "
            "Cloud runs need Drive sync to remember what's already been "
            "sent — set drive_folder_id in the config stored in your "
            "SCHOOL_DIGEST_CONFIG_YAML_B64 secret."
        )

    if sync_with_drive:
        drive_state.download_state(config.db_path, config.drive_folder_id)
    dedup_store.init_db(config.db_path)

    run_start = datetime.now()
    if since_days is not None:
        since = run_start - timedelta(days=since_days)
    else:
        last_run_str = dedup_store.get_last_run(config.db_path)
        since = datetime.fromisoformat(last_run_str) if last_run_str else run_start - timedelta(days=1)

    emails = fetch_labeled_emails(config.gmail_label, since)
    log.info("Fetched %d new labeled email(s) since %s", len(emails), since.isoformat())

    posted: list[str] = []
    failed_subjects: list[str] = []      # never reached Slack
    unrecorded_subjects: list[str] = []  # reached Slack, but not the sent log

    for email in emails:
        # A single email failing here — for any reason, not just the
        # known max_tokens signature extract.py already retries once on
        # its own — must never crash the whole run. Two real things
        # depend on reaching the end of this loop regardless: any OTHER
        # email in this same batch still needs to get processed, and
        # the sync at the end (cursor advance + Drive upload) is what
        # protects everything that succeeded earlier in this exact run
        # from getting silently lost and re-sent next time.
        was_posted = False
        try:
            extraction = extract_email(client, config, email)

            dedup_statuses: dict[str, DedupStatus] = {}
            for item in extraction.items:
                dedup_statuses[item.topic_key] = dedup_store.check_dedup(
                    config.db_path,
                    item.topic_key,
                    extraction.school,
                    config.rules.dedup_lookback_days,
                )

            decision = decide(config, extraction, dedup_statuses, email.subject)

            if decision.slack_text is None:
                log.info("Skipped (nothing survived): %s — %d candidate item(s)",
                          _log_name(email), len(extraction.items))
                continue

            if not dry_run:
                post_message(config.slack_channel, decision.slack_text)
            posted.append(decision.slack_text)
            was_posted = True
            if decision.is_reply_notice:
                log.info("Posted FYI notice: reply to %s — nothing new", _log_name(email))
            else:
                log.info("Posted: %s — %d item(s) included", _log_name(email), len(decision.logged_items))

            if not dry_run:
                for item in decision.logged_items:
                    dedup_store.log_sent(
                        config.db_path,
                        item.topic_key,
                        extraction.school,
                        item.requests_volunteer_help,
                        item.is_promotional,
                        item.one_line_summary,
                        message_id=email.message_id,
                    )
        except Exception:
            # Deliberately broad: anything at all going wrong on this
            # one email should not be allowed to take down the rest of
            # the batch or skip the sync below. Logged with the full
            # traceback so it's still fully diagnosable — just not fatal.
            # Which list it goes in depends on whether the post already
            # went out: if it did, the email WAS handled — only the
            # record of it is missing, which is a different problem
            # (possible repeat later) from "you never saw this at all".
            if was_posted:
                unrecorded_subjects.append(email.subject)
                log.exception("Posted email %s but couldn't record it in the sent log — "
                              "continuing with the rest", _log_name(email))
            else:
                failed_subjects.append(email.subject)
                log.exception("Failed to process email %s — skipping it, continuing with the rest",
                              _log_name(email))

    if failed_subjects or unrecorded_subjects:
        log.warning("%d of %d email(s) failed this run (%d never posted, %d posted but "
                    "not recorded) — check the log above for details",
                    len(failed_subjects) + len(unrecorded_subjects), len(emails),
                    len(failed_subjects), len(unrecorded_subjects))
        # A warning sitting in a log someone would have to go looking for
        # isn't actually seen — the whole point of this tool is that
        # nobody has to go check things themselves. Post it where it'll
        # actually get seen, with enough detail to go find the email
        # directly rather than a vague "something went wrong."
        if not dry_run:
            post_message(config.slack_channel,
                         _failure_notice(failed_subjects, unrecorded_subjects))

    if not dry_run:
        dedup_store.set_last_run(config.db_path, run_start.isoformat())
    if sync_with_drive:
        drive_state.upload_state(config.db_path, config.drive_folder_id)

    return posted
