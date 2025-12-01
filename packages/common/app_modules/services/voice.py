"""Voice training service extracted from the monolithic API module."""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import structlog
from fastapi import HTTPException
from fastapi import UploadFile
from starlette.requests import Request

from packages.core.models import VoiceSample, VoiceTrainingJob, VoiceTrainingStatus
from packages.core.mongo import MongoClient

logger = structlog.get_logger(__name__)


try:  # pragma: no cover - optional when Celery is absent
    from celery.exceptions import CeleryError  # type: ignore
except Exception:  # noqa: BLE001 - celery may be missing in local dev/tests
    class CeleryError(Exception):
        """Fallback Celery error type."""


try:  # pragma: no cover - optional when kombu is not installed
    from kombu.exceptions import OperationalError as KombuOperationalError  # type: ignore
except Exception:  # noqa: BLE001 - kombu may be missing in local dev/tests
    class KombuOperationalError(Exception):
        """Fallback kombu operational error."""


VOICE_ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/flac",
    "audio/x-flac",
    "audio/ogg",
    "audio/webm",
    "audio/aac",
    "audio/m4a",
}
VOICE_MAX_SAMPLE_BYTES = int(os.getenv("VOICE_SAMPLE_MAX_BYTES", str(25 * 1024 * 1024)))
VOICE_MIN_SAMPLE_COUNT = int(os.getenv("VOICE_MIN_SAMPLE_COUNT", "3"))
VOICE_QUEUE_ERRORS: tuple[type[BaseException], ...] = (
    CeleryError,
    KombuOperationalError,
    ConnectionError,
    TimeoutError,
)
VOICE_JOB_STALE_TIMEOUT = float(os.getenv("VOICE_JOB_STALE_TIMEOUT", "20"))


class VoiceService:
    """Encapsulate voice sample and training workflows."""

    def __init__(
        self,
        *,
        normalize_project: Callable[[str | None], str | None],
        get_mongo_client: Callable[[Request], MongoClient],
        voice_train_task: Any | None,
        worker_mongo_client: Any | None,
        worker_settings: Any | None,
        queue_error_types: Sequence[type[BaseException]] = VOICE_QUEUE_ERRORS,
        max_sample_bytes: int = VOICE_MAX_SAMPLE_BYTES,
        min_sample_count: int = VOICE_MIN_SAMPLE_COUNT,
        job_stale_timeout: float = VOICE_JOB_STALE_TIMEOUT,
        allowed_content_types: Iterable[str] = VOICE_ALLOWED_CONTENT_TYPES,
    ) -> None:
        self._normalize_project = normalize_project
        self._get_mongo_client = get_mongo_client
        self._voice_train_task = voice_train_task
        self._worker_mongo_client = worker_mongo_client
        self._worker_settings = worker_settings
        self._queue_error_types = tuple(queue_error_types)
        self._max_sample_bytes = max_sample_bytes
        self._min_sample_count = min_sample_count
        self._job_stale_timeout = job_stale_timeout
        self._allowed_content_types = {ctype.lower() for ctype in allowed_content_types}

    def _validate_project(self, project: str | None) -> str:
        project_name = self._normalize_project(project)
        if not project_name:
            raise HTTPException(status_code=400, detail="project_required")
        return project_name

    def _queue_voice_training_job(self, job_id: str) -> bool:
        if (
            self._worker_mongo_client is None
            or self._worker_settings is None
            or self._voice_train_task is None
        ):
            return False
        task = getattr(self._voice_train_task, "delay", None)
        if not callable(task):
            return False
        try:
            task(job_id)
            return True
        except self._queue_error_types as exc:  # type: ignore[arg-type]
            logger.warning("voice_training_enqueue_failed", job_id=job_id, error=str(exc))
            return False

    async def _run_voice_job_inline(self, job_id: str, mongo_client: MongoClient) -> None:
        stages = [
            (VoiceTrainingStatus.preparing, 0.1, "Готовим набор примеров", 0.6),
            (VoiceTrainingStatus.training, 0.65, "Обучаем голосовую модель", 1.2),
            (VoiceTrainingStatus.validating, 0.9, "Проверяем результат", 0.8),
        ]
        try:
            started_at = time.time()
            await mongo_client.update_voice_training_job(
                job_id,
                status=VoiceTrainingStatus.preparing,
                progress=0.05,
                message="Запускаем обучение",
                started_at=started_at,
            )
            for status, progress, message, delay in stages:
                await asyncio.sleep(delay)
                await mongo_client.update_voice_training_job(
                    job_id,
                    status=status,
                    progress=progress,
                    message=message,
                )
            await asyncio.sleep(0.6)
            await mongo_client.update_voice_training_job(
                job_id,
                status=VoiceTrainingStatus.completed,
                progress=1.0,
                message="Голосовой профиль готов",
                finished_at=time.time(),
            )
            logger.info("voice_training_inline_completed", job_id=job_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("voice_training_inline_failed", job_id=job_id, error=str(exc))
            await mongo_client.update_voice_training_job(
                job_id,
                status=VoiceTrainingStatus.failed,
                progress=0.0,
                message="Ошибка при обучении",
                finished_at=time.time(),
            )

    async def _voice_job_watchdog(
        self,
        job_id: str,
        project: str,
        mongo_client: MongoClient,
    ) -> None:
        await asyncio.sleep(max(1.0, self._job_stale_timeout))
        try:
            jobs = await mongo_client.list_voice_training_jobs(project, limit=1)
        except Exception as exc:  # noqa: BLE001
            logger.warning("voice_training_watchdog_fetch_error", job_id=job_id, project=project, error=str(exc))
            return
        if not jobs:
            return
        job = jobs[0]
        if job.id != job_id:
            return
        if job.status == VoiceTrainingStatus.queued:
            logger.warning("voice_training_watchdog_inline", job_id=job_id, project=project)
            await self._run_voice_job_inline(job_id, mongo_client)

    def _validate_voice_payload(
        self,
        filename: str | None,
        content_type: str | None,
        payload: bytes,
    ) -> tuple[str, str | None, bytes]:
        safe_name = Path(filename or "sample").name
        if len(payload) == 0:
            raise HTTPException(status_code=400, detail="empty_sample")
        if len(payload) > self._max_sample_bytes:
            raise HTTPException(status_code=413, detail="sample_too_large")
        lowered = (content_type or "").lower() or None
        if lowered and lowered in self._allowed_content_types:
            return safe_name, lowered, payload
        suffix = Path(safe_name).suffix.lower()
        if suffix in {".mp3", ".wav", ".flac", ".ogg", ".webm", ".m4a", ".aac"}:
            return safe_name, lowered, payload
        raise HTTPException(status_code=415, detail="unsupported_content_type")

    async def list_samples(self, request: Request, project: str | None) -> list[VoiceSample]:
        project_name = self._validate_project(project)
        mongo_client = self._get_mongo_client(request)
        return await mongo_client.list_voice_samples(project_name)

    async def upload_samples(
        self,
        request: Request,
        project: str,
        files: Sequence[UploadFile],
    ) -> list[VoiceSample]:
        project_name = self._validate_project(project)
        if not files:
            raise HTTPException(status_code=400, detail="files_required")

        mongo_client = self._get_mongo_client(request)
        for file in files:
            payload = await file.read()
            filename, content_type, payload = self._validate_voice_payload(
                file.filename,
                file.content_type,
                payload,
            )
            await mongo_client.add_voice_sample(project_name, filename, payload, content_type)
            await file.close()
        logger.info(
            "voice_samples_uploaded",
            project=project_name,
            uploaded=len(files),
        )
        return await mongo_client.list_voice_samples(project_name)

    async def delete_sample(
        self,
        request: Request,
        sample_id: str,
        project: str | None = None,
    ) -> list[VoiceSample]:
        project_name = self._validate_project(project)
        mongo_client = self._get_mongo_client(request)
        removed = await mongo_client.delete_voice_sample(project_name, sample_id)
        if not removed:
            raise HTTPException(status_code=404, detail="sample_not_found")
        return await mongo_client.list_voice_samples(project_name)

    async def list_jobs(
        self,
        request: Request,
        project: str | None,
        limit: int = 10,
    ) -> list[VoiceTrainingJob]:
        project_name = self._validate_project(project)
        safe_limit = max(1, min(limit, 25))
        mongo_client = self._get_mongo_client(request)
        return await mongo_client.list_voice_training_jobs(project_name, limit=safe_limit)

    async def get_status(self, request: Request, project: str | None) -> VoiceTrainingJob | None:
        project_name = self._validate_project(project)
        mongo_client = self._get_mongo_client(request)
        jobs = await mongo_client.list_voice_training_jobs(project_name, limit=1)
        return jobs[0] if jobs else None

    async def start_training(
        self,
        request: Request,
        project: str,
    ) -> tuple[dict[str, Any], int]:
        project_name = self._validate_project(project)
        mongo_client = self._get_mongo_client(request)
        samples = await mongo_client.list_voice_samples(project_name)
        if len(samples) < self._min_sample_count:
            raise HTTPException(
                status_code=400,
                detail=f"not_enough_samples:{len(samples)}/{self._min_sample_count}",
            )

        existing_jobs = await mongo_client.list_voice_training_jobs(project_name, limit=1)
        if existing_jobs:
            existing_job = existing_jobs[0]
            payload = existing_job.model_dump(by_alias=True)
            if existing_job.status in {
                VoiceTrainingStatus.queued,
                VoiceTrainingStatus.preparing,
                VoiceTrainingStatus.training,
                VoiceTrainingStatus.validating,
            }:
                updated_at = payload.get("updatedAt") or payload.get("updated_at")
                if updated_at is None:
                    updated_at = existing_job.created_at or time.time()
                try:
                    updated_at_value = float(updated_at)
                except (TypeError, ValueError):
                    updated_at_value = time.time()

                age = time.time() - updated_at_value
                if age >= self._job_stale_timeout:
                    logger.warning(
                        "voice_training_job_stale",
                        project=project_name,
                        job_id=existing_job.id,
                        status=existing_job.status.value,
                        age=age,
                    )
                    updated_job = await mongo_client.update_voice_training_job(
                        existing_job.id,
                        status=VoiceTrainingStatus.queued,
                        progress=existing_job.progress or 0.0,
                        message="Перезапускаем обучение",
                    )
                    if updated_job:
                        payload = updated_job.model_dump(by_alias=True)
                    requeued = self._queue_voice_training_job(existing_job.id)
                    if requeued:
                        asyncio.create_task(self._voice_job_watchdog(existing_job.id, project_name, mongo_client))
                    else:
                        asyncio.create_task(self._run_voice_job_inline(existing_job.id, mongo_client))
                    return ({"job": payload, "resumed": True, "detail": "job_resumed"}, 202)

                if existing_job.status == VoiceTrainingStatus.queued:
                    asyncio.create_task(self._voice_job_watchdog(existing_job.id, project_name, mongo_client))

                logger.info(
                    "voice_training_job_active",
                    project=project_name,
                    job_id=existing_job.id,
                    status=existing_job.status.value,
                )
                return ({"job": payload, "resumed": False, "detail": "job_in_progress"}, 202)

        job = await mongo_client.create_voice_training_job(project_name)
        queued = self._queue_voice_training_job(job.id)
        if queued:
            asyncio.create_task(self._voice_job_watchdog(job.id, project_name, mongo_client))
        else:
            asyncio.create_task(self._run_voice_job_inline(job.id, mongo_client))
        logger.info(
            "voice_training_queued",
            project=project_name,
            job_id=job.id,
            transport="celery" if queued else "inline",
        )
        return ({"job": job.model_dump(by_alias=True), "detail": "job_queued"}, 202)

