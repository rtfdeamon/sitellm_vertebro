"""Unit tests for backup service helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from backup.service import (
    BackupError,
    BackupResult,
    normalize_remote_folder,
    perform_backup,
    should_run_backup,
)
from models import BackupSettings


def test_normalize_remote_folder_trims_slashes() -> None:
    assert normalize_remote_folder(' /foo/bar/ ') == 'foo/bar'
    assert normalize_remote_folder('') == 'sitellm-backups'
    assert normalize_remote_folder(None) == 'sitellm-backups'


def test_should_run_backup_based_on_schedule() -> None:
    base_settings = BackupSettings(enabled=True, hour=3, minute=15, timezone='UTC')
    before_window = datetime(2024, 1, 5, 3, 0, tzinfo=timezone.utc)
    after_window = datetime(2024, 1, 5, 3, 30, tzinfo=timezone.utc)

    assert should_run_backup(base_settings, now=before_window) is False
    assert should_run_backup(base_settings, now=after_window) is True

    attempted_settings = base_settings.model_copy(update={'last_attempt_date': '2024-01-05'})
    assert should_run_backup(attempted_settings, now=after_window) is False


def test_perform_backup_uploads_archive(monkeypatch, tmp_path) -> None:
    archive_payload = b'dummy-archive'

    def fake_run(cmd, check, capture_output, timeout):  # noqa: ANN001
        archive_arg = next((arg for arg in cmd if arg.startswith('--archive=')), None)
        assert archive_arg is not None
        archive_path = Path(archive_arg.split('=', 1)[1])
        archive_path.write_bytes(archive_payload)
        return SimpleNamespace(returncode=0, stdout=b'', stderr=b'')

    monkeypatch.setattr('backup.service.subprocess.run', fake_run)

    class FakeResponse:
        def __init__(self, status_code: int, json_payload: dict | None = None, text: str = '') -> None:
            self.status_code = status_code
            self._json = json_payload or {}
            self.text = text

        def json(self) -> dict:
            return self._json

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise BackupError(f'HTTP {self.status_code}')

    created_clients: list[object] = []

    class FakeClient:
        def __init__(self, *_, **__):
            self.folder_created = False
            self.uploaded_payload = None
            created_clients.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def put(self, url, params=None, headers=None, data=None):  # noqa: ANN001
            if url.endswith('/resources'):
                assert params and params.get('path') == 'backups'
                self.folder_created = True
                return FakeResponse(201)
            if url == 'https://upload.example':
                assert data is not None
                if hasattr(data, 'read'):
                    self.uploaded_payload = data.read()
                else:
                    self.uploaded_payload = data
                return FakeResponse(201)
            raise AssertionError(f'unexpected PUT url {url}')

        def get(self, url, params=None, headers=None):  # noqa: ANN001
            if url.endswith('/resources/upload'):
                return FakeResponse(200, {'href': 'https://upload.example'})
            raise AssertionError(f'unexpected GET url {url}')

    monkeypatch.setattr('backup.service.httpx.Client', lambda timeout: FakeClient())

    result = perform_backup(
        mongo_uri='mongodb://localhost:27017/admin',
        database='testdb',
        token='TOKEN',
        remote_folder='backups',
        dump_binary='mongodump',
        timeout=5,
    )

    assert isinstance(result, BackupResult)
    assert result.remote_path.startswith('backups/')
    assert result.size_bytes == len(archive_payload)
    assert created_clients
    client = created_clients[0]
    assert isinstance(client, FakeClient)
    assert client.uploaded_payload == archive_payload


def test_perform_backup_raises_on_mongodump_failure(monkeypatch) -> None:
    def fake_run(*args, **kwargs):  # noqa: ANN001
        raise FileNotFoundError('mongodump missing')

    monkeypatch.setattr('backup.service.subprocess.run', fake_run)
    with pytest.raises(BackupError):
        perform_backup(
            mongo_uri='mongodb://localhost:27017/admin',
            database='testdb',
            token='TOKEN',
        )
