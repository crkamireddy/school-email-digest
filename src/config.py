"""Loads config.yaml into typed objects. This is the ONLY place that should
know your family's school/class names — every other module takes that
information as a parameter instead of hardcoding it.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass
class ClassInfo:
    name: str
    # Grade lives per-class, not per-school — a school can have more than
    # one relevant class (e.g. two kids at the same school in different
    # grades), each with its own optional grade note.
    grade_note: str | None = None


@dataclass
class School:
    name: str
    type: str
    relevant_classes: list[ClassInfo]


@dataclass
class Rules:
    deadline_window_days: int
    volunteer_asks_only_for_relevant_classes: bool
    skip_unrelated_grades: bool
    dedup_lookback_days: int


@dataclass
class Config:
    schools: list[School]
    rules: Rules
    slack_channel: str
    extract_model: str
    gmail_label: str
    db_path: str
    # None means local-only: the SQLite file at db_path is the only copy.
    # Set it to keep that file synced through a Google Drive folder
    # instead — required for cloud runs, whose disk doesn't survive
    # between runs. See drive_state.py.
    drive_folder_id: str | None = None

    def all_relevant_classes(self) -> list[str]:
        classes: list[str] = []
        for s in self.schools:
            classes.extend(c.name for c in s.relevant_classes)
        return classes

    def schools_block(self) -> str:
        """Renders the school/class list as text for injection into prompts.
        Explicitly labels school TYPE (K-8, preschool) as distinct from
        per-class GRADE, and repeats the class list as a flat, counted
        summary — a bracketed type tag next to a per-class grade note
        was observed getting confused with the grade itself, silently
        dropping a class from the model's own accounting before it ever
        got to reading the email."""
        lines = []
        total_classes = 0
        for s in self.schools:
            lines.append(f"- {s.name} (school type: {s.type})")
            for c in s.relevant_classes:
                grade = f", grade: {c.grade_note}" if c.grade_note else ""
                lines.append(f"  - Class: {c.name}{grade}")
                total_classes += 1

        lines.append("")
        lines.append(
            f"Full list of this family's {total_classes} relevant class(es) — "
            "account for every single one, don't drop any:"
        )
        for s in self.schools:
            for c in s.relevant_classes:
                grade = f" ({c.grade_note})" if c.grade_note else ""
                lines.append(f"  - {c.name}{grade} at {s.name}")

        return "\n".join(lines)


def _parse_class(entry: str | dict) -> ClassInfo:
    """Accepts either a plain class name string (no grade note needed),
    or a mapping with name + optional grade_note — so config.yaml only
    needs the extra structure for schools where it actually matters."""
    if isinstance(entry, str):
        return ClassInfo(name=entry)
    return ClassInfo(name=entry["name"], grade_note=entry.get("grade_note"))


def load_config(path: str | Path = "config.yaml") -> Config:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Copy config.example.yaml to config.yaml "
            "and fill in your own school/class details first."
        )
    raw = yaml.safe_load(path.read_text())

    schools = [
        School(
            name=s["name"],
            type=s["type"],
            relevant_classes=[_parse_class(c) for c in s.get("relevant_classes", [])],
        )
        for s in raw["schools"]
    ]

    rules = Rules(
        deadline_window_days=raw["rules"]["deadline_window_days"],
        volunteer_asks_only_for_relevant_classes=raw["rules"][
            "volunteer_asks_only_for_relevant_classes"
        ],
        skip_unrelated_grades=raw["rules"]["skip_unrelated_grades"],
        dedup_lookback_days=raw["rules"]["dedup_lookback_days"],
    )

    # Required key, even though its value can be empty: an older
    # config.yaml written before this setting existed should fail loudly
    # here, not quietly fall back to local-only and lose the shared dedup
    # history it was actually relying on.
    if "drive_folder_id" not in raw["storage"]:
        raise ValueError(
            f"{path} is missing storage.drive_folder_id. Set it to your "
            "Google Drive folder ID to sync the sent log through Drive, or "
            'to "" to keep it local-only. See config.example.yaml.'
        )
    drive_folder_id = raw["storage"]["drive_folder_id"] or None

    return Config(
        schools=schools,
        rules=rules,
        slack_channel=raw["notification"]["slack_channel"],
        extract_model=raw["models"]["extract_model"],
        gmail_label=raw["gmail"]["label"],
        db_path=raw["storage"]["db_path"],
        drive_folder_id=drive_folder_id,
    )
