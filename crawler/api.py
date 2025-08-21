from __future__ import annotations

import subprocess
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, HttpUrl, Field

from core.status import status_dict

router = APIRouter(prefix="/crawler", tags=["crawler"])


class CrawlRequest(BaseModel):
    url: HttpUrl
    depth: int = Field(ge=1, default=3)
    pages: int = Field(ge=1, default=500)


def _run_crawler(url: str, depth: int, pages: int) -> None:
    subprocess.Popen(
        [
            "python",
            "crawler/run_crawl.py",
            "--url",
            url,
            "--max-depth",
            str(depth),
            "--max-pages",
            str(pages),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@router.post("/run")
async def run_crawler(req: CrawlRequest, background: BackgroundTasks) -> dict[str, str]:
    background.add_task(_run_crawler, req.url, req.depth, req.pages)
    return {"status": "started"}


@router.get("/status")
def crawler_status() -> dict[str, int | None]:
    return status_dict()["crawler"]
