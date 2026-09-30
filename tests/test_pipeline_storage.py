"""Which storage path a run takes — local-only vs. Drive-synced — based
on config.drive_folder_id. Gmail, Anthropic, and Drive are all mocked;
no network access or API keys needed."""
from unittest.mock import patch

import pytest

from src.config import load_config
from src.pipeline import run


def _config(tmp_path, drive_folder_id=None):
    config = load_config("config.example.yaml")
    config.db_path = str(tmp_path / "sent_log.db")
    config.drive_folder_id = drive_folder_id
    return config


@pytest.fixture
def no_network(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    with patch("src.pipeline.Anthropic"), \
         patch("src.pipeline.fetch_labeled_emails", return_value=[]), \
         patch("src.pipeline.drive_state") as drive_state:
        yield drive_state


def test_local_only_run_never_touches_drive(tmp_path, no_network):
    run(config=_config(tmp_path, drive_folder_id=None))
    no_network.download_state.assert_not_called()
    no_network.upload_state.assert_not_called()


def test_drive_synced_run_downloads_and_uploads_with_configured_folder(tmp_path, no_network):
    config = _config(tmp_path, drive_folder_id="abc123")
    run(config=config)
    no_network.download_state.assert_called_once_with(config.db_path, "abc123")
    no_network.upload_state.assert_called_once_with(config.db_path, "abc123")


def test_dry_run_skips_drive_even_when_configured(tmp_path, no_network):
    run(config=_config(tmp_path, drive_folder_id="abc123"), dry_run=True)
    no_network.download_state.assert_not_called()
    no_network.upload_state.assert_not_called()


def test_github_actions_without_drive_folder_refuses_to_run(tmp_path, no_network, monkeypatch):
    """A cloud runner's disk is blank every run — local-only there means
    no dedup history at all, and the same emails re-posted every time."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    with pytest.raises(RuntimeError, match="drive_folder_id"):
        run(config=_config(tmp_path, drive_folder_id=None))
