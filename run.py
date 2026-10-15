#!/usr/bin/env python3
"""Entry point. Run manually with `python run.py`, or point a scheduler
(cron, launchd, a Replit scheduled deployment, GitHub Actions) at this.

Loads secrets from .env if python-dotenv is available and a .env file
exists; otherwise expects ANTHROPIC_API_KEY / SLACK_BOT_TOKEN to already
be in the environment.

Usage:
    python run.py                          # normal run, uses stored cursor
    python run.py --dry-run                # prints instead of posting
    python run.py --dry-run --since-days 7 # look back further, for exploring
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.pipeline import run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                         help="Print what would be posted; touch nothing.")
    parser.add_argument("--since-days", type=int, default=None,
                         help="Look back this many days instead of the stored "
                              "cursor — handy for exploring more of your inbox. "
                              "Strongly recommend pairing with --dry-run: without "
                              "it, already-processed items with neither the "
                              "volunteer nor the promotional flag (schedule "
                              "changes, deadlines, classroom updates, most news) "
                              "will get re-posted, since those are always-included "
                              "regardless of dedup status.")
    args = parser.parse_args()

    posted = run(dry_run=args.dry_run, since_days=args.since_days)
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}{len(posted)} message(s) posted.")
