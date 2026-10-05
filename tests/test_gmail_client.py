from src.gmail_client import _is_auto_reply


def test_out_of_office_reply_is_detected():
    assert _is_auto_reply({"From": "teacher@example-elementary.org",
                           "Auto-Submitted": "auto-replied"})


def test_header_name_and_value_are_case_insensitive():
    assert _is_auto_reply({"auto-submitted": "Auto-Replied"})


def test_value_with_parameters_is_detected():
    assert _is_auto_reply({"Auto-Submitted": "auto-replied; owner-email=\"t@example.org\""})


def test_auto_generated_newsletter_is_not_skipped():
    """Bulk newsletter tools may mark real announcements auto-generated —
    those must still reach the digest."""
    assert not _is_auto_reply({"Auto-Submitted": "auto-generated"})


def test_explicit_no_and_missing_header_are_not_skipped():
    assert not _is_auto_reply({"Auto-Submitted": "no"})
    assert not _is_auto_reply({"From": "office@example-preschool.org"})

