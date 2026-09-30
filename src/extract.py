"""Extraction stage. One Claude call, one job: turn a raw email — single
note or multi-topic newsletter alike — into a list of structured
candidate items. No inclusion/exclusion judgment happens here beyond
"is this even plausibly relevant" — the actual rules (deadline windows,
dedup) are applied afterward in decide.py, using real facts this stage
doesn't have access to.
"""
from __future__ import annotations

import json
import re
from datetime import date

from anthropic import Anthropic

from .config import Config
from .models import RawEmail, EmailExtraction
from .prompts import render_prompt

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

# Used only as an automatic fallback when the configured model hits the
# specific max_tokens-exhaustion signature below — not a general
# override of config.extract_model.
_FALLBACK_MODEL = "claude-haiku-4-5-20251001"


def _parse_json_response(text: str) -> dict:
    """Claude is instructed to return only JSON, but this strips any
    accidental wrapping (like ```json fences) defensively rather than
    trusting the model never to add any."""
    match = _JSON_BLOCK_RE.search(text)
    if not match:
        raise ValueError(f"No JSON object found in extraction response: {text!r}")
    return json.loads(match.group(0))


def _call_and_parse(client: Anthropic, model: str, system_prompt: str, user_content: str) -> dict:
    response = client.messages.create(
        model=model,
        # 4000, not 1500: the smaller budget was tuned against Haiku's
        # behavior and proved too tight for a model with adaptive
        # thinking on the longest, most complex newsletters — every
        # observed truncation failure was on a long multi-item input,
        # never a short single-topic one. Even at 4000 this can still
        # happen occasionally (confirmed in production, not just eval) —
        # there's no fixed number that's provably enough for a model
        # with open-ended internal reasoning, which is exactly why
        # extract_email() below retries on this specific signature
        # rather than just trusting a bigger number to make it go away.
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    try:
        return _parse_json_response(text)
    except ValueError as e:
        # Surface stop_reason so a truncated response is immediately
        # diagnosable, rather than requiring a guess at whether this
        # was a token-budget issue or something else.
        raise ValueError(
            f"{e} (stop_reason={response.stop_reason!r}, "
            f"output_tokens={response.usage.output_tokens})"
        ) from e


def extract_email(
    client: Anthropic,
    config: Config,
    email: RawEmail,
    today: date | None = None,
) -> EmailExtraction:
    today = today or date.today()

    system_prompt = render_prompt(
        "extract_system.md",
        today=today.isoformat(),
        schools_block=config.schools_block(),
    )

    user_content = (
        f"Subject: {email.subject}\n"
        f"From: {email.sender}\n"
        f"Received: {email.received_at}\n\n"
        f"{email.body_text}"
    )

    try:
        data = _call_and_parse(client, config.extract_model, system_prompt, user_content)
    except ValueError as e:
        # Retry once, specifically and only for the known failure
        # signature: adaptive thinking consumed the entire token budget
        # before producing any visible answer at all. Haiku has no
        # adaptive thinking, so it structurally can't hit this same
        # failure — a real, different model, not just trying again and
        # hoping. Any other kind of failure (a real API error, a
        # genuinely malformed response) is NOT retried here; it
        # propagates up so pipeline.py's per-email safety net can log
        # it clearly rather than this silently masking something new.
        if "max_tokens" in str(e) and config.extract_model != _FALLBACK_MODEL:
            data = _call_and_parse(client, _FALLBACK_MODEL, system_prompt, user_content)
        else:
            raise

    return EmailExtraction.from_dict(data)
