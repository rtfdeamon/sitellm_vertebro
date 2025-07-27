import argparse
import asyncio
import json
import time
from typing import List

import httpx


async def _request(client: httpx.AsyncClient, url: str) -> float:
    start = time.perf_counter()
    resp = await client.post(url, json={"text": "test"})
    resp.raise_for_status()
    return (time.perf_counter() - start) * 1000


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()

    url = "http://localhost:8000/api/chat"
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

    print(json.dumps({"p95_ms": round(p95), "throughput": round(throughput, 2)}))


if __name__ == "__main__":
    asyncio.run(main())
