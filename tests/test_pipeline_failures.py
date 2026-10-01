"""The Slack warning after a per-email failure must say what actually
happened: an email that never got posted vs. one that was posted but
couldn't be recorded in the sent log. Regression test for a run where a
successful post was followed by "Couldn't process 1 email" because the
sent-log write failed afterwards. Gmail, Anthropic, Slack, and Drive are
all mocked."""
from unittest.mock import MagicMock, patch

import pytest

from src.config import load_config
from src.pipeline import _failure_notice, run
from tests.fixtures.sample_emails import ROOM12_FIELD_TRIP_DEADLINE as EMAIL


@pytest.fixture
def mocked(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    config = load_config("config.example.yaml")
    config.db_path = str(tmp_path / "sent_log.db")
    config.drive_folder_id = None

    decision = MagicMock(slack_text="the digest post", is_reply_notice=False,
                         logged_items=[MagicMock()])
    with patch("src.pipeline.Anthropic"), \
         patch("src.pipeline.fetch_labeled_emails", return_value=[EMAIL]), \
         patch("src.pipeline.extract_email") as extract, \
         patch("src.pipeline.decide", return_value=decision), \
         patch("src.pipeline.post_message") as post:
        extract.return_value.items = []
        yield config, extract, post


def _slack_texts(post):
    return [c.args[1] for c in post.call_args_list]


def test_posted_but_not_recorded_is_not_called_a_failure_to_process(mocked):
    config, _, post = mocked
    with patch("src.pipeline.dedup_store.log_sent",
               side_effect=Exception("table sent_log has no column named x")):
        run(config=config)

    texts = _slack_texts(post)
    assert texts[0] == "the digest post"
    assert "Posted 1 email(s) above but couldn't record" in texts[1]
    assert EMAIL.subject in texts[1]
    assert "Couldn't process" not in texts[1]


def test_failure_before_posting_says_couldnt_process(mocked):
    config, extract, post = mocked
    extract.side_effect = Exception("model call failed")
    run(config=config)

    texts = _slack_texts(post)
    assert len(texts) == 1
    assert "Couldn't process 1 email(s)" in texts[0]
    assert EMAIL.subject in texts[0]


def test_notice_lists_both_kinds_separately():
    text = _failure_notice(["Never posted"], ["Posted, unrecorded"])
    couldnt, posted = text.split("\n\n")
    assert "Couldn't process 1" in couldnt and "• Never posted" in couldnt
    assert "Posted 1" in posted and "• Posted, unrecorded" in posted
