#!/usr/bin/env python3
"""Eval harness — runs the fixture emails through the REAL extract/decide
pipeline against the live Anthropic API and reports pass/fail against
expected outcomes.

Since extraction now pulls out a LIST of items per email, "expected"
here means substrings that must (or must not) appear in the final
decided Slack text — this is what actually matters: did the right
content survive, not an exact item-by-item match to a shape only I know.

This costs real API calls and needs ANTHROPIC_API_KEY set. Run it after
any prompt change to catch regressions before they show up as a wrong
Slack message.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python eval_live.py                          # your own family, config.example.yaml
    python eval_live.py --model claude-sonnet-5   # override the model only, for comparing
    python eval_live.py --config config.friend-test.yaml \
                         --fixtures tests.fixtures.friend_test_emails
        # tests against a DIFFERENT simulated family entirely — real
        # generalization test, not just more fixtures for your own setup
"""
import argparse
import importlib
import sys
from datetime import date

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from anthropic import Anthropic

from src.config import load_config
from src.decide import decide
from src.extract import extract_email
from src.models import DedupStatus

TODAY = date(2026, 9, 8)  # fixed so results are reproducible; matches the fixtures' dates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=None,
                         help="Override extract_model for this run only — "
                              "config.yaml itself is never touched.")
    parser.add_argument("--config", type=str, default="config.example.yaml",
                         help="Which config file to load — swap this to test "
                              "against a totally different simulated family.")
    parser.add_argument("--fixtures", type=str, default="tests.fixtures.sample_emails",
                         help="Dotted module path exposing an ALL_FIXTURES list, "
                              "same shape as tests/fixtures/sample_emails.py.")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.model:
        config.extract_model = args.model
    client = Anthropic()

    fixtures_module = importlib.import_module(args.fixtures)
    all_fixtures = fixtures_module.ALL_FIXTURES

    print(f"Running against: {config.extract_model}")
    print(f"Config: {args.config}")
    print(f"Fixtures: {args.fixtures}\n")

    passed = 0
    failed = 0

    for email, must_include, must_exclude in all_fixtures:
        try:
            extraction = extract_email(client, config, email, today=TODAY)
        except Exception as e:
            print(f"FAIL  {email.subject}\n      extraction call errored: {e}\n")
            failed += 1
            continue

        # Assume nothing's already been sent for this pass — dedup
        # behavior itself is covered separately by test_dedup_store.py.
        dedup_statuses = {item.topic_key: DedupStatus(already_sent=False) for item in extraction.items}
        decision = decide(config, extraction, dedup_statuses, email.subject, today=TODAY)

        text = decision.slack_text or ""
        missing = [s for s in must_include if s.lower() not in text.lower()]
        leaked = [s for s in must_exclude if s.lower() in text.lower()]

        def _flags(i):
            marks = []
            if i.requests_volunteer_help:
                marks.append("volunteer")
            if i.is_promotional:
                marks.append("promo")
            return "+".join(marks) if marks else "default"

        item_summary = ", ".join(f"{_flags(i)}:{i.topic_key}" for i in extraction.items) or "(none)"
        scan_preview = extraction.grade_specific_scan or "(empty)"

        if not missing and not leaked:
            print(f"PASS  {email.subject}")
            print(f"      {len(extraction.items)} item(s) extracted: {item_summary}")
            print(f"      grade_specific_scan: {scan_preview}")
            print(f"      decided text: {text or '(nothing — SKIP)'}\n")
            passed += 1
        else:
            print(f"FAIL  {email.subject}")
            print(f"      {len(extraction.items)} item(s) extracted: {item_summary}")
            print(f"      grade_specific_scan: {scan_preview}")
            if missing:
                print(f"      MISSING (should be included, wasn't): {missing}")
            if leaked:
                print(f"      LEAKED (should be excluded, wasn't): {leaked}")
            print(f"      decided text: {text or '(nothing — SKIP)'}\n")
            failed += 1

    print(f"\n{passed} passed, {failed} failed out of {len(all_fixtures)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
