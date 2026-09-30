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
