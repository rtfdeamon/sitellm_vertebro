"""Ollama cluster manager with load balancing and metrics."""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional

import httpx
import structlog

from backend.settings import settings as backend_settings
from models import OllamaServer

logger = structlog.get_logger(__name__)

DEFAULT_AVG_LATENCY = 2.5  # seconds
MAX_FAILURES_BEFORE_COOLDOWN = 3
FAILURE_COOLDOWN_SECONDS = 15
REQUEST_TIMEOUT_SECONDS = None


class ModelNotFoundError(RuntimeError):
    """Raised when the requested Ollama model is missing on the host."""

    def __init__(self, model: str | None, base_url: str | None, message: str | None = None):
        details = message or "Модель не найдена в Ollama"
        target = model or "(не указана)"
        base = base_url or "(неизвестно)"
        super().__init__(f"{details}: {target} @ {base}")
        self.model = model
        self.base_url = base_url


@dataclass
class _ServerStats:
    samples: deque[tuple[float, float]] = field(default_factory=deque)
    avg_duration: float = DEFAULT_AVG_LATENCY
    requests_last_hour: int = 0
    total_duration_ms: float = 0.0


@dataclass
class _ServerState:
    name: str
    base_url: str
    enabled: bool = True
    created_at: float | None = None
    updated_at: float | None = None
    stats: _ServerStats = field(default_factory=_ServerStats)
    inflight: int = 0
    failures: int = 0
    cooldown_until: float = 0.0
    last_error: str | None = None
    ephemeral: bool = False

    def estimated_load(self, now: float) -> float:
        latency = max(self.stats.avg_duration, 0.1)
        if self.inflight <= 0:
            return latency
        return latency * (self.inflight + 1)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "enabled": self.enabled,
            "inflight": self.inflight,
            "avg_latency_ms": round(self.stats.avg_duration * 1000, 2),
            "requests_last_hour": self.stats.requests_last_hour,
            "total_duration_ms": round(self.stats.total_duration_ms, 2),
            "cooldown_until": self.cooldown_until,
            "failures": self.failures,
            "last_error": self.last_error,
            "updated_at": self.updated_at,
            "created_at": self.created_at,
            "ephemeral": self.ephemeral,
        }


class OllamaClusterManager:
    def __init__(self, mongo_client, *, default_base: str | None = None):
        self._mongo = mongo_client
        self._default_base = default_base.rstrip('/') if default_base else None
        self._lock = asyncio.Lock()
        self._servers: Dict[str, _ServerState] = {}

    # region lifecycle
    async def reload(self) -> None:
        docs = await self._mongo.list_ollama_servers()
        new_map: Dict[str, _ServerState] = {}
        now = time.time()
        for doc in docs:
            state = self._servers.get(doc.name)
            stats = self._build_stats_from_doc(doc)
            if state:
                state.base_url = doc.base_url.rstrip('/')
                state.enabled = doc.enabled
                state.created_at = doc.created_at or state.created_at or now
                state.updated_at = doc.updated_at or now
                if stats:
                    state.stats = stats
            else:
                state = _ServerState(
                    name=doc.name,
                    base_url=doc.base_url.rstrip('/'),
                    enabled=doc.enabled,
                    created_at=doc.created_at or now,
                    updated_at=doc.updated_at or now,
                    stats=stats or _ServerStats(avg_duration=DEFAULT_AVG_LATENCY),
                )
            new_map[state.name] = state
        if not new_map and self._default_base:
            state = _ServerState(
                name="default",
                base_url=self._default_base,
                enabled=True,
                created_at=now,
                updated_at=now,
                stats=_ServerStats(avg_duration=DEFAULT_AVG_LATENCY),
                ephemeral=True,
            )
            new_map[state.name] = state
        async with self._lock:
            # carry over inflight counters for servers that remain
            for key, state in new_map.items():
                prev = self._servers.get(key)
                if prev:
                    state.inflight = prev.inflight
                    state.failures = prev.failures
                    state.cooldown_until = prev.cooldown_until
            self._servers = new_map

    def _build_stats_from_doc(self, doc: OllamaServer) -> _ServerStats | None:
        stats_info = doc.stats or {}
        avg = stats_info.get("avg_latency_ms")
        avg_sec = (float(avg) / 1000.0) if avg else DEFAULT_AVG_LATENCY
        requests = int(stats_info.get("requests_last_hour", 0) or 0)
        total_ms = float(stats_info.get("total_duration_ms", 0.0) or 0.0)
        stats = _ServerStats(avg_duration=max(avg_sec, 0.1))
        stats.requests_last_hour = max(requests, 0)
        stats.total_duration_ms = max(total_ms, 0.0)
        return stats

    # endregion

    async def describe(self) -> List[dict]:
        async with self._lock:
            return [state.to_dict() for state in self._servers.values()]

    async def generate(self, prompt: str, *, model: str | None = None) -> AsyncIterator[str]:
        exclude: set[str] = set()
        while True:
            server = await self._acquire_server(exclude)
            if not server:
                raise RuntimeError("Нет доступных серверов Ollama")
            start = time.time()
            try:
                async for chunk in self._stream_from_server(server, prompt, model):
                    yield chunk
                duration = time.time() - start
                await self._release_success(server, duration)
                return
            except ModelNotFoundError:
                duration = time.time() - start
                await self._release_failure(server, duration, hard_failure=True)
                raise
            except Exception as exc:  # noqa: BLE001
                duration = time.time() - start
                logger.warning(
                    "ollama_server_request_failed",
                    server=server.name,
                    base_url=server.base_url,
                    error=str(exc),
                )
                await self._release_failure(server, duration, error=exc)
                exclude.add(server.name)
                if len(exclude) >= await self._enabled_server_count():
                    raise
                continue

    async def _enabled_server_count(self) -> int:
        async with self._lock:
            now = time.time()
            return sum(
                1
                for state in self._servers.values()
                if state.enabled and state.cooldown_until <= now
            )

    async def _acquire_server(self, exclude: set[str]) -> Optional[_ServerState]:
        async with self._lock:
            now = time.time()
            candidates = [
                state
                for name, state in self._servers.items()
                if name not in exclude and state.enabled and state.cooldown_until <= now
            ]
            if not candidates:
                return None
            candidates.sort(key=lambda s: s.estimated_load(now))
            server = candidates[0]
            server.inflight += 1
            return server

    async def _release_success(self, server: _ServerState, duration: float) -> None:
        async with self._lock:
            server.inflight = max(0, server.inflight - 1)
            server.failures = 0
            server.cooldown_until = 0.0
            now = time.time()
            server.stats.samples.append((now, duration))
            self._prune_samples(server, now)
            server.stats.requests_last_hour = len(server.stats.samples)
            server.stats.total_duration_ms = sum(d * 1000.0 for _, d in server.stats.samples)
            if server.stats.requests_last_hour:
                server.stats.avg_duration = (
                    server.stats.total_duration_ms / server.stats.requests_last_hour
                ) / 1000.0
            else:
                server.stats.avg_duration = DEFAULT_AVG_LATENCY
        if not server.ephemeral:
            await self._mongo.update_ollama_server_stats(
                server.name,
                avg_latency_ms=server.stats.avg_duration * 1000.0,
                requests_last_hour=server.stats.requests_last_hour,
                total_duration_ms=server.stats.total_duration_ms,
            )

    async def _release_failure(
        self,
        server: _ServerState,
        duration: float,
        *,
        error: Exception | None = None,
        hard_failure: bool = False,
    ) -> None:
        async with self._lock:
            server.inflight = max(0, server.inflight - 1)
            server.failures += 1
            server.last_error = str(error) if error else None
            if server.failures >= MAX_FAILURES_BEFORE_COOLDOWN or hard_failure:
                server.cooldown_until = time.time() + FAILURE_COOLDOWN_SECONDS
        if hard_failure and not server.ephemeral:
            await self._mongo.update_ollama_server_stats(
                server.name,
                avg_latency_ms=server.stats.avg_duration * 1000.0,
                requests_last_hour=server.stats.requests_last_hour,
                total_duration_ms=server.stats.total_duration_ms,
            )

    def _prune_samples(self, server: _ServerState, now: float) -> None:
        window = 3600
        samples = server.stats.samples
        while samples and now - samples[0][0] > window:
            samples.popleft()

    async def _stream_from_server(
        self,
        server: _ServerState,
        prompt: str,
        model: str | None,
    ) -> AsyncIterator[str]:
        url = f"{server.base_url.rstrip('/')}/api/generate"
        model_name = model or backend_settings.llm_model or backend_settings.ollama_model
        payload = {"model": model_name, "prompt": prompt, "stream": True}
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            async with client.stream("POST", url, json=payload) as resp:
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    if exc.response is not None and exc.response.status_code == 404:
                        raise ModelNotFoundError(model_name, server.base_url) from exc
                    raise
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("response")
                    if token:
                        yield token
                        await asyncio.sleep(0)
                    if data.get("done"):
                        return


_cluster_manager: OllamaClusterManager | None = None


async def init_cluster(mongo_client, *, default_base: str | None = None) -> OllamaClusterManager:
    global _cluster_manager
    manager = OllamaClusterManager(mongo_client, default_base=default_base)
    await manager.reload()
    _cluster_manager = manager
    return manager


def get_cluster_manager() -> OllamaClusterManager:
    if _cluster_manager is None:
        raise RuntimeError("Ollama cluster manager is not initialized")
    return _cluster_manager


async def reload_cluster() -> None:
    manager = get_cluster_manager()
    await manager.reload()
*** End of File
