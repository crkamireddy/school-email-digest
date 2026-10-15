"""Loads system prompts from prompts/*.md and fills in config-driven
values. Uses string.Template ($variable) rather than str.format() because
the prompt files contain literal JSON braces (e.g. {"school": ...}) that
would collide with str.format()'s {placeholder} syntax.
"""
from __future__ import annotations

from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def render_prompt(filename: str, **values: str) -> str:
    text = (PROMPTS_DIR / filename).read_text()
    return Template(text).safe_substitute(**values)
