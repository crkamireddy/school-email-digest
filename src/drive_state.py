"""Persists the dedup database in Google Drive instead of relying on a
local disk — the thing a fresh cloud runner never has, but also the
thing that keeps a local run and a cloud run from silently diverging
into two different dedup histories. Download before a run, upload
after. dedup_store.py is completely unaware this exists; it just always
finds a normal local SQLite file at whatever path it's given.

Optional: only used when config.yaml sets storage.drive_folder_id. The
folder ID is passed in rather than stored here, so pointing this at a
different Drive folder never means editing code.
"""
from __future__ import annotations

import io
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from .google_auth import get_credentials

DRIVE_FILENAME = "school-email-digest-sent-log.db"


def _get_drive_service():
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)


def _find_file_id(service, folder_id: str) -> str | None:
    query = f"name = '{DRIVE_FILENAME}' and '{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def download_state(local_path: str, folder_id: str) -> None:
    """Pulls the current dedup database down from Drive to local_path.
    If nothing exists there yet — the very first run anywhere, local or
    cloud — there's nothing to download; dedup_store.py creates a
    fresh, empty database the first time it's opened, same as always."""
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)

    service = _get_drive_service()
    file_id = _find_file_id(service, folder_id)
    if file_id is None:
        return

    request = service.files().get_media(fileId=file_id)
    with io.FileIO(local_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


def upload_state(local_path: str, folder_id: str) -> None:
    """Pushes the updated dedup database back up to Drive, replacing
    whatever was there before. Updates the existing file if one exists
    rather than creating a new one each time, so this never leaves
    duplicate copies scattered in the folder."""
    service = _get_drive_service()
    file_id = _find_file_id(service, folder_id)
    media = MediaFileUpload(local_path, mimetype="application/x-sqlite3")

    if file_id:
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        service.files().create(
            body={"name": DRIVE_FILENAME, "parents": [folder_id]},
            media_body=media,
        ).execute()
