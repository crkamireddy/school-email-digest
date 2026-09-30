from unittest.mock import MagicMock

import pytest

from src.slack_client import _resolve_channel_id, _channel_id_cache


@pytest.fixture(autouse=True)
def clear_cache():
    _channel_id_cache.clear()
    yield
    _channel_id_cache.clear()


def test_raw_channel_id_passes_through_without_api_call():
    client = MagicMock()
    result = _resolve_channel_id(client, "C0123456789")
    assert result == "C0123456789"
    client.conversations_list.assert_not_called()


def test_hash_prefixed_name_gets_resolved_to_id():
    client = MagicMock()
    client.conversations_list.return_value = {
        "channels": [
            {"name": "random", "id": "C0000000001"},
            {"name": "school-updates", "id": "C0000000002"},
        ],
        "response_metadata": {"next_cursor": ""},
    }
    result = _resolve_channel_id(client, "#school-updates")
    assert result == "C0000000002"


def test_name_without_hash_also_resolves():
    client = MagicMock()
    client.conversations_list.return_value = {
        "channels": [{"name": "school-updates", "id": "C0000000002"}],
        "response_metadata": {"next_cursor": ""},
    }
    result = _resolve_channel_id(client, "school-updates")
    assert result == "C0000000002"


def test_paginates_until_match_found():
    client = MagicMock()
    client.conversations_list.side_effect = [
        {"channels": [{"name": "random", "id": "C1"}],
         "response_metadata": {"next_cursor": "page2"}},
        {"channels": [{"name": "school-updates", "id": "C2"}],
         "response_metadata": {"next_cursor": ""}},
    ]
    result = _resolve_channel_id(client, "#school-updates")
    assert result == "C2"
    assert client.conversations_list.call_count == 2


def test_unresolvable_name_raises_clear_error():
    client = MagicMock()
    client.conversations_list.return_value = {
        "channels": [{"name": "random", "id": "C1"}],
        "response_metadata": {"next_cursor": ""},
    }
    with pytest.raises(RuntimeError, match="No Slack channel named 'school-test'"):
        _resolve_channel_id(client, "#school-test")


def test_second_lookup_uses_cache_not_another_api_call():
    client = MagicMock()
    client.conversations_list.return_value = {
        "channels": [{"name": "school-updates", "id": "C2"}],
        "response_metadata": {"next_cursor": ""},
    }
    _resolve_channel_id(client, "#school-updates")
    _resolve_channel_id(client, "#school-updates")
    assert client.conversations_list.call_count == 1
