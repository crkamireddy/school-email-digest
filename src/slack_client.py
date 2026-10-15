"""Slack integration. Needs a Slack app with a bot token that has the
chat:write scope, invited to the target channel.

Setup (one-time, you do this yourself):
  1. Create a Slack app at api.slack.com/apps, add the chat:write scope,
     install it to your workspace.
  2. Put the bot token (starts with xoxb-) in your .env as SLACK_BOT_TOKEN.
  3. Invite the bot to the channel, and put that channel's ID (e.g.
     C0123456789) in config.yaml as slack_channel.

A "#channel-name" in config.yaml also works, but additionally needs the
channels:read scope (plus groups:read for a private channel): the name
gets looked up to find the channel ID the API actually wants, since
passing a bare name straight to chat.postMessage is known to be
unreliable on recent Slack API versions.
"""
from __future__ import annotations

import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

_channel_id_cache: dict[str, str] = {}


def _resolve_channel_id(client: WebClient, channel: str) -> str:
    """Accepts a human-readable #channel-name (worth keeping in a config
    file meant to be hand-edited) or an already-resolved channel ID, and
    returns a real channel ID. Cached per process so a run that posts
    several messages doesn't re-list channels every time."""
    name = channel.lstrip("#")

    if name in _channel_id_cache:
        return _channel_id_cache[name]

    # Already looks like a raw channel ID (e.g. "C0123456789") — no
    # lookup needed.
    if channel == name and name.isupper() and name.isalnum():
        return channel

    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel,private_channel", limit=200, cursor=cursor
        )
        for c in resp["channels"]:
            if c["name"] == name:
                _channel_id_cache[name] = c["id"]
                return c["id"]
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    raise RuntimeError(
        f"No Slack channel named '{name}' found among channels this bot "
        "can see. Check the spelling in config.yaml, and make sure the "
        "bot has actually been invited to that channel."
    )


def post_message(channel: str, text: str) -> None:
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN not set — check your .env file.")

    client = WebClient(token=token)
    try:
        channel_id = _resolve_channel_id(client, channel)
        client.chat_postMessage(channel=channel_id, text=text)
    except SlackApiError as e:
        raise RuntimeError(f"Slack post failed: {e.response['error']}") from e
