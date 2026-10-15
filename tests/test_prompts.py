from src.prompts import render_prompt


def test_extract_prompt_renders_without_error_despite_literal_json_braces():
    """This is the exact bug str.format() would hit: the prompt file
    contains literal {"school": ...} JSON examples. If this doesn't
    raise, the Template-based substitution is doing its job."""
    text = render_prompt(
        "extract_system.md",
        today="2026-09-08",
        schools_block="- Example Elementary [K-8]\n  - Room 12 (2nd grade)",
    )
    assert "2026-09-08" in text
    assert "Room 12 (2nd grade)" in text
    assert '"topic_key"' in text  # the literal JSON schema is still intact
    assert '"items"' in text


def test_extract_prompt_includes_out_of_office_rule():
    text = render_prompt(
        "extract_system.md",
        today="2026-09-08",
        schools_block="- Example Elementary [K-8]",
    )
    assert "Out-of-office / automatic replies" in text


def test_extract_prompt_dates_the_weekly_class_recap_key():
    """Without a date in the recap's topic_key, every weekly newsletter
    exact-matches the first one and gets tagged "Follow-up"."""
    text = render_prompt(
        "extract_system.md",
        today="2026-09-08",
        schools_block="- Example Elementary [K-8]",
    )
    assert "room12-class-update-2026-10-09" in text


def test_extract_prompt_includes_personal_note_rule():
    text = render_prompt(
        "extract_system.md",
        today="2026-09-08",
        schools_block="- Example Elementary [K-8]",
    )
    assert "Personal notes and conversations with this family" in text


def test_extract_prompt_forbids_copying_credentials():
    text = render_prompt(
        "extract_system.md",
        today="2026-09-08",
        schools_block="- Example Elementary [K-8]",
    )
    assert "Never copy credentials" in text
