from unittest.mock import MagicMock, patch

from src.config import Config, Rules
from src.extract import extract_email
from src.models import RawEmail


def make_config(extract_model="claude-sonnet-5") -> Config:
    return Config(
        schools=[],
        rules=Rules(deadline_window_days=7, volunteer_asks_only_for_relevant_classes=True,
                     skip_unrelated_grades=True, dedup_lookback_days=21),
        slack_channel="#test",
        extract_model=extract_model,
        gmail_label="School",
        db_path=":memory:",
    )


def make_email() -> RawEmail:
    return RawEmail(
        message_id="test-1", subject="Test email", sender="school@example.com",
        body_text="Some content.", received_at="2026-09-12T10:00:00",
    )


def _mock_response(text: str, stop_reason: str = "end_turn", output_tokens: int = 100):
    response = MagicMock()
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text
    response.content = [text_block]
    response.stop_reason = stop_reason
    response.usage.output_tokens = output_tokens
    return response


def test_no_retry_when_first_call_succeeds():
    """The common case — nothing about the retry path should ever run
    when the configured model just works, which is what happens on the
    overwhelming majority of real emails."""
    good_json = '{"school": "Example Elementary", "is_reply_with_no_new_info": false, "items": []}'
    client = MagicMock()
    client.messages.create.return_value = _mock_response(good_json)

    result = extract_email(client, make_config(), make_email())

    assert result.school == "Example Elementary"
    assert client.messages.create.call_count == 1


def test_retries_with_fallback_model_on_max_tokens_exhaustion():
    """This is the exact real bug: adaptive thinking consumed the whole
    budget with nothing visible left over. Confirms the automatic
    recovery actually engages, and specifically falls back to Haiku —
    a real different model, not just trying the same call again and
    hoping for a different result."""
    good_json = '{"school": "Example Elementary", "is_reply_with_no_new_info": false, "items": []}'
    client = MagicMock()
    client.messages.create.side_effect = [
        _mock_response("", stop_reason="max_tokens", output_tokens=4000),  # exhausted, empty
        _mock_response(good_json),  # fallback succeeds
    ]

    result = extract_email(client, make_config(extract_model="claude-sonnet-5"), make_email())

    assert result.school == "Example Elementary"
    assert client.messages.create.call_count == 2
    first_call_model = client.messages.create.call_args_list[0].kwargs["model"]
    second_call_model = client.messages.create.call_args_list[1].kwargs["model"]
    assert first_call_model == "claude-sonnet-5"
    assert second_call_model == "claude-haiku-4-5-20251001"


def test_does_not_retry_on_a_different_kind_of_failure():
    """Only the specific, known max_tokens signature gets an automatic
    retry. A genuinely different failure (malformed JSON that isn't a
    truncation, for instance) should propagate immediately rather than
    silently masking something new behind a retry that isn't actually
    addressing the real cause."""
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        "not json at all", stop_reason="end_turn", output_tokens=50
    )

    try:
        extract_email(client, make_config(), make_email())
        assert False, "expected a ValueError"
    except ValueError:
        pass

    assert client.messages.create.call_count == 1


def test_no_infinite_loop_when_fallback_model_itself_is_configured():
    """If Haiku is already the configured model and it somehow hits
    this signature too, there's no second model to fall back to —
    must raise, not recurse or retry forever."""
    client = MagicMock()
    client.messages.create.return_value = _mock_response(
        "", stop_reason="max_tokens", output_tokens=4000
    )

    try:
        extract_email(client, make_config(extract_model="claude-haiku-4-5-20251001"), make_email())
        assert False, "expected a ValueError"
    except ValueError:
        pass

    assert client.messages.create.call_count == 1
