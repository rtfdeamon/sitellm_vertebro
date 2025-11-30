"""Measure latency and throughput of the chat endpoint."""

import argparse
import asyncio
import json
import time
from typing import List

import httpx
import structlog

from packages.utils.observability.logging import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)


async def _request(client: httpx.AsyncClient, url: str) -> float:
    """Send a POST request and return latency in milliseconds."""
    start = time.perf_counter()
    resp = await client.post(url, json={"text": "test"})
    resp.raise_for_status()
    return (time.perf_counter() - start) * 1000


async def main() -> None:
    """Run benchmark and print p95 latency and throughput as JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()

    url = "http://localhost:8000/api/chat"
    logger.info("benchmark", requests=args.requests, concurrency=args.concurrency)
    latencies: List[float] = []
    sem = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient() as client:
        async def worker() -> None:
            async with sem:
                latency = await _request(client, url)
                latencies.append(latency)

        start = time.perf_counter()
        await asyncio.gather(*(worker() for _ in range(args.requests)))
        duration = time.perf_counter() - start

    sorted_lat = sorted(latencies)
    idx = int(0.95 * (len(sorted_lat) - 1)) if sorted_lat else 0
    p95 = sorted_lat[idx] if sorted_lat else 0.0
    throughput = args.requests / duration if duration else 0.0

    result = {"p95_ms": round(p95), "throughput": round(throughput, 2)}
    logger.info("result", **result)
    logger.info("result_json", json=json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
