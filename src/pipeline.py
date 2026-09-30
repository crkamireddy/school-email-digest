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
    failed_subjects: list[str] = []

    for email in emails:
        # A single email failing here — for any reason, not just the
        # known max_tokens signature extract.py already retries once on
        # its own — must never crash the whole run. Two real things
        # depend on reaching the end of this loop regardless: any OTHER
        # email in this same batch still needs to get processed, and
        # the sync at the end (cursor advance + Drive upload) is what
        # protects everything that succeeded earlier in this exact run
        # from getting silently lost and re-sent next time.
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
                          email.subject, len(extraction.items))
                continue

            if not dry_run:
                post_message(config.slack_channel, decision.slack_text)
            posted.append(decision.slack_text)
            if decision.is_reply_notice:
                log.info("Posted FYI notice: reply to \"%s\" — nothing new", email.subject)
            else:
                log.info("Posted: %s — %d item(s) included", email.subject, len(decision.logged_items))

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
            failed_subjects.append(email.subject)
            log.exception("Failed to process email %r — skipping it, continuing with the rest",
                           email.subject)

    if failed_subjects:
        log.warning("%d of %d email(s) failed this run and were skipped — "
                     "check the log above for details", len(failed_subjects), len(emails))
        # A warning sitting in a log someone would have to go looking for
        # isn't actually seen — the whole point of this tool is that
        # nobody has to go check things themselves. Post it where it'll
        # actually get seen, with enough detail to go find the email
        # directly rather than a vague "something went wrong."
        if not dry_run:
            subjects_list = "\n".join(f"• {s}" for s in failed_subjects)
            post_message(
                config.slack_channel,
                f"⚠️ Couldn't process {len(failed_subjects)} email(s) this run — "
                f"worth checking these directly:\n{subjects_list}",
            )

    if not dry_run:
        dedup_store.set_last_run(config.db_path, run_start.isoformat())
    if sync_with_drive:
        drive_state.upload_state(config.db_path, config.drive_folder_id)

    return posted
