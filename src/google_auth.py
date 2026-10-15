"""Shared Google OAuth credential handling. Gmail and Drive both
authenticate through the same token — one set of credentials, two
scopes, used by two different API clients. Used to live duplicated
inside gmail_client.py; pulled out once Drive access was added too,
rather than copy the same refresh logic a second time.

Setup (one-time, you do this yourself):
  1. In Google Cloud Console, enable BOTH the Gmail API and the Drive
     API, and create OAuth client credentials (Desktop app type).
     Download as credentials.json into the project root.
  2. First run after this file changed needs a fresh authorization —
     delete any existing token.json first, since a token issued for
     the old, narrower scope list won't carry the new Drive permission.
     The next run opens a browser to authorize once, covering both
     scopes, then caches token.json so future runs don't need to.
"""
from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# gmail.readonly: read (never send/delete/modify) labeled emails.
# drive.file: only files this app itself creates or opens — not
# blanket access to everything else in Drive. Both are the minimal
# scope for what each piece actually does.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.file",
]


def get_credentials(token_path: str = "token.json", creds_path: str = "credentials.json") -> Credentials:
    creds = None
    if Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        Path(token_path).write_text(creds.to_json())
    return creds
