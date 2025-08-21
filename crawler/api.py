from __future__ import annotations

from uuid import uuid4
from fastapi import APIRouter
from pydantic import BaseModel

from .run_crawl import DEFAULT_MAX_PAGES, DEFAULT_MAX_DEPTH, DEFAULT_MONGO_URI
from .tasks import start_crawl

router = APIRouter(prefix="/crawler", tags=["crawler"])


class CrawlRequest(BaseModel):
    url: str
    max_pages: int | None = None
    max_depth: int | None = None
    domain: str | None = None
    mongo_uri: str | None = None


class CrawlResponse(BaseModel):
    job_id: str


@router.post("/run", response_model=CrawlResponse)
def run_crawler(request: CrawlRequest) -> CrawlResponse:
    job_id = str(uuid4())
    start_crawl.delay(
        request.url,
        max_pages=request.max_pages or DEFAULT_MAX_PAGES,
        max_depth=request.max_depth or DEFAULT_MAX_DEPTH,
        domain=request.domain,
        mongo_uri=request.mongo_uri or DEFAULT_MONGO_URI,
        job_id=job_id,
    )
    return CrawlResponse(job_id=job_id)
