"""Backup helpers for MongoDB archives and Yandex.Disk storage."""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import httpx
from zoneinfo import ZoneInfo

from models import BackupSettings


YANDEX_API_BASE = "https://cloud-api.yandex.net/v1/disk"


class BackupError(RuntimeError):
    """Raised when backup or restore operations cannot be completed."""


@dataclass(slots=True, frozen=True)
class BackupResult:
    """Payload returned after a successful backup run."""

    remote_path: str
    size_bytes: int
    filename: str


def build_mongo_uri(
    host: str,
    port: int,
    username: str | None,
    password: str | None,
    auth_database: str | None = None,
) -> str:
    """Return a MongoDB URI suitable for command-line tools."""

    auth_db = auth_database or "admin"
    has_user = username is not None and str(username) != ""
    has_pass = password is not None and str(password) != ""
    if has_user and has_pass:
        user = quote_plus(str(username))
        passwd = quote_plus(str(password))
        auth_part = f"{user}:{passwd}@"
        auth_db_part = f"/{auth_db}"
    else:
        auth_part = ""
        auth_db_part = ""
    return f"mongodb://{auth_part}{host}:{port}{auth_db_part}"


def normalize_remote_folder(folder: str | None) -> str:
    """Return sanitized remote folder path for Yandex.Disk uploads."""

    candidate = (folder or "").strip().strip("/")
    return candidate or "sitellm-backups"


def _resolve_timeout(timeout: float | None) -> tuple[float, httpx.Timeout]:
    base = timeout if timeout and timeout > 0 else 600.0
    http_timeout = httpx.Timeout(base, connect=min(base, 10.0))
    return base, http_timeout


def _request_headers(token: str) -> dict[str, str]:
    token_value = (token or "").strip()
    if not token_value:
        raise BackupError("ya_disk_token_missing")
    return {"Authorization": f"OAuth {token_value}"}


def _ensure_remote_folder(client: httpx.Client, headers: dict[str, str], folder: str) -> None:
    response = client.put(
        f"{YANDEX_API_BASE}/resources",
        params={"path": folder},
        headers=headers,
    )
    if response.status_code in {201, 409}:
        return
    try:
        detail = response.json()
    except Exception:  # noqa: BLE001 - best effort diagnostics
        detail = response.text
    raise BackupError(f"ya_disk_folder_create_failed: {detail}")


def _request_upload_url(
    client: httpx.Client,
    headers: dict[str, str],
    remote_path: str,
) -> str:
    response = client.get(
        f"{YANDEX_API_BASE}/resources/upload",
        params={"path": remote_path, "overwrite": "true"},
        headers=headers,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:  # pragma: no cover - propagate with context
        raise BackupError(f"ya_disk_upload_url_failed: {exc.response.text}") from exc
    payload = response.json()
    href = (payload or {}).get("href")
    if not href:
        raise BackupError("ya_disk_upload_href_missing")
    return str(href)


def _upload_archive(client: httpx.Client, upload_url: str, archive_path: Path) -> None:
    with archive_path.open("rb") as handle:
        response = client.put(
            upload_url,
            data=handle,
            headers={"Content-Type": "application/gzip"},
        )
    if response.status_code not in {200, 201, 202, 204}:
        raise BackupError(f"ya_disk_upload_failed: {response.text}")


def perform_backup(
    *,
    mongo_uri: str,
    database: str,
    token: str,
    remote_folder: str | None = None,
    dump_binary: str | None = None,
    timeout: float | None = None,
) -> BackupResult:
    """Create compressed MongoDB archive and upload it to Yandex.Disk."""

    if not mongo_uri or not database:
        raise BackupError("mongo_configuration_missing")

    binary = dump_binary or os.getenv("MONGODUMP_BIN", "mongodump")
    folder = normalize_remote_folder(remote_folder)
    headers = _request_headers(token)
    command_timeout, http_timeout = _resolve_timeout(timeout)

    timestamp = datetime.now(timezone.utc)
    filename = f"{database}-{timestamp:%Y%m%d-%H%M%S}.archive.gz"

    with tempfile.TemporaryDirectory(prefix="sitellm-backup-") as tmpdir:
        archive_path = Path(tmpdir) / filename
        cmd = [
            binary,
            f"--uri={mongo_uri}",
            f"--db={database}",
            f"--archive={archive_path}",
            "--gzip",
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=command_timeout,
            )
        except FileNotFoundError as exc:
            raise BackupError("mongodump_not_found") from exc
        except subprocess.TimeoutExpired as exc:
            raise BackupError("mongodump_timeout") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or b"").decode("utf-8", errors="ignore")
            raise BackupError(f"mongodump_failed: {stderr.strip() or exc.args}") from exc

        if not archive_path.exists():
            raise BackupError("mongodump_archive_missing")

        size_bytes = archive_path.stat().st_size
        remote_path = f"{folder}/{filename}"

        with httpx.Client(timeout=http_timeout) as client:
            _ensure_remote_folder(client, headers, folder)
            upload_url = _request_upload_url(client, headers, remote_path)
            _upload_archive(client, upload_url, archive_path)

    return BackupResult(remote_path=remote_path, size_bytes=size_bytes, filename=filename)


def _download_archive(
    client: httpx.Client,
    headers: dict[str, str],
    remote_path: str,
    destination: Path,
) -> None:
    response = client.get(
        f"{YANDEX_API_BASE}/resources/download",
        params={"path": remote_path},
        headers=headers,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise BackupError(f"ya_disk_download_url_failed: {exc.response.text}") from exc
    href = (response.json() or {}).get("href")
    if not href:
        raise BackupError("ya_disk_download_href_missing")

    stream = client.get(href, headers=headers)
    if stream.status_code != 200:
        raise BackupError(f"ya_disk_download_failed: {stream.text}")
    with destination.open("wb") as handle:
        handle.write(stream.content)


def perform_restore(
    *,
    mongo_uri: str,
    database: str,
    token: str,
    remote_path: str,
    restore_binary: str | None = None,
    timeout: float | None = None,
) -> None:
    """Download archive from Yandex.Disk and restore it into MongoDB."""

    if not remote_path:
        raise BackupError("restore_remote_path_missing")

    binary = restore_binary or os.getenv("MONGORESTORE_BIN", "mongorestore")
    headers = _request_headers(token)
    command_timeout, http_timeout = _resolve_timeout(timeout)

    with tempfile.TemporaryDirectory(prefix="sitellm-restore-") as tmpdir:
        archive_path = Path(tmpdir) / Path(remote_path).name
        with httpx.Client(timeout=http_timeout) as client:
            _download_archive(client, headers, remote_path, archive_path)

        if not archive_path.exists():
            raise BackupError("restore_archive_missing")

        cmd = [
            binary,
            f"--uri={mongo_uri}",
            f"--db={database}",
            "--drop",
            f"--archive={archive_path}",
            "--gzip",
        ]
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=command_timeout,
            )
        except FileNotFoundError as exc:
            raise BackupError("mongorestore_not_found") from exc
        except subprocess.TimeoutExpired as exc:
            raise BackupError("mongorestore_timeout") from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or b"").decode("utf-8", errors="ignore")
            raise BackupError(f"mongorestore_failed: {stderr.strip() or exc.args}") from exc


def should_run_backup(settings: BackupSettings, *, now: datetime | None = None) -> bool:
    """Return ``True`` if a scheduled backup should be triggered."""

    if not settings.enabled:
        return False

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)

    tz_name = settings.timezone or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001 - fallback for invalid zone names
        tz = ZoneInfo("UTC")

    local_now = current.astimezone(tz)
    scheduled = local_now.replace(
        hour=max(0, min(23, settings.hour)),
        minute=max(0, min(59, settings.minute)),
        second=0,
        microsecond=0,
    )
    if local_now < scheduled:
        return False

    today_label = local_now.date().isoformat()
    if settings.last_attempt_date == today_label:
        return False
    return True
