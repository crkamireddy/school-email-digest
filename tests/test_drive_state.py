from unittest.mock import MagicMock, patch

import pytest

from src.drive_state import _find_file_id, download_state, upload_state

FOLDER_ID = "example-folder-id"


def test_find_file_id_returns_id_when_file_exists():
    service = MagicMock()
    service.files().list().execute.return_value = {"files": [{"id": "abc123"}]}
    assert _find_file_id(service, FOLDER_ID) == "abc123"


def test_find_file_id_returns_none_when_no_file_exists():
    service = MagicMock()
    service.files().list().execute.return_value = {"files": []}
    assert _find_file_id(service, FOLDER_ID) is None


def test_find_file_id_searches_the_folder_it_was_given():
    """The folder comes from config now, not a hardcoded constant — make
    sure it's the one actually used in the Drive search."""
    service = MagicMock()
    service.files().list().execute.return_value = {"files": []}
    _find_file_id(service, "some-other-folder")
    query = service.files().list.call_args.kwargs["q"]
    assert "'some-other-folder' in parents" in query


@patch("src.drive_state._get_drive_service")
def test_download_state_does_nothing_when_no_file_exists_yet(mock_get_service, tmp_path):
    """First run anywhere, local or cloud — nothing to download, and
    this must not error out just because there's nothing there yet."""
    service = MagicMock()
    service.files().list().execute.return_value = {"files": []}
    mock_get_service.return_value = service

    local_path = str(tmp_path / "sent_log.db")
    download_state(local_path, FOLDER_ID)  # should return cleanly, not raise

    service.files().get_media.assert_not_called()


@patch("src.drive_state._get_drive_service")
def test_download_state_creates_parent_directory(mock_get_service, tmp_path):
    """Real bug this guards against: a fresh cloud checkout has no
    'data/' directory at all, since git doesn't track empty ones."""
    service = MagicMock()
    service.files().list().execute.return_value = {"files": []}
    mock_get_service.return_value = service

    local_path = str(tmp_path / "data" / "sent_log.db")
    assert not (tmp_path / "data").exists()
    download_state(local_path, FOLDER_ID)
    assert (tmp_path / "data").exists()


@patch("src.drive_state._get_drive_service")
def test_upload_state_updates_existing_file_not_create(mock_get_service, tmp_path):
    """Must never leave duplicate copies behind — if a file's already
    there, this has to update it, not create a second one."""
    service = MagicMock()
    service.files().list().execute.return_value = {"files": [{"id": "existing123"}]}
    mock_get_service.return_value = service

    local_path = tmp_path / "sent_log.db"
    local_path.write_text("fake db content")

    with patch("src.drive_state.MediaFileUpload"):
        upload_state(str(local_path), FOLDER_ID)

    service.files().update.assert_called_once()
    service.files().create.assert_not_called()


@patch("src.drive_state._get_drive_service")
def test_upload_state_creates_when_nothing_exists_yet(mock_get_service, tmp_path):
    service = MagicMock()
    service.files().list().execute.return_value = {"files": []}
    mock_get_service.return_value = service

    local_path = tmp_path / "sent_log.db"
    local_path.write_text("fake db content")

    with patch("src.drive_state.MediaFileUpload"):
        upload_state(str(local_path), FOLDER_ID)

    service.files().create.assert_called_once()
    service.files().update.assert_not_called()
    assert service.files().create.call_args.kwargs["body"]["parents"] == [FOLDER_ID]
