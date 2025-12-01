"""Reading helpers extracted from the API module."""

from __future__ import annotations

import base64
import os
from datetime import date, datetime
from typing import Any, Callable, Sequence

import structlog
from fastapi import HTTPException
from starlette.requests import Request

from packages.core.models import Document, ReadingPage
from packages.core.mongo import MongoClient

logger = structlog.get_logger(__name__)

READING_PAGE_MAX_LIMIT = 20
READING_PREVIEW_LIMIT = min(5, READING_PAGE_MAX_LIMIT)
READING_PREVIEW_MAX_SEGMENTS_PER_PAGE = 12
READING_PREVIEW_MAX_IMAGES_PER_PAGE = 6
READING_PREVIEW_SEGMENT_CHAR_LIMIT = 1800
READING_PREVIEW_TEXT_CHAR_LIMIT = 3500
READING_PREVIEW_TOTAL_CHAR_LIMIT = 20000
READING_PREVIEW_HTML_CHAR_LIMIT = 5000

DEFAULT_READING_COLLECTION = os.getenv("MONGO_READING_COLLECTION", "reading_pages")


class ReadingService:
    """Encapsulate reading mode helpers used across the API."""

    def __init__(
        self,
        *,
        normalize_project: Callable[[str | None], str | None],
        build_download_url: Callable[[Request, str], str],
        reading_collection: str | None = None,
    ) -> None:
        self._normalize_project = normalize_project
        self._build_download_url = build_download_url
        self._reading_collection = reading_collection or DEFAULT_READING_COLLECTION

    @staticmethod
    def _truncate_value(value: Any, limit: int) -> str | None:
        if limit <= 0:
            return None
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) <= limit:
            return cleaned
        slice_limit = max(1, limit - 3)
        truncated = cleaned[:slice_limit].rstrip()
        if not truncated:
            truncated = cleaned[:slice_limit]
        return f"{truncated}..."

    @classmethod
    def _json_safe(cls, value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, (bytes, bytearray)):
            return base64.b64encode(value).decode("ascii")
        if isinstance(value, dict):
            return {k: cls._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set, frozenset)):
            return [cls._json_safe(item) for item in value]
        return value

    def _serialize_pages(
        self,
        request: Request,
        pages: Sequence[ReadingPage],
    ) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        remaining_chars = READING_PREVIEW_TOTAL_CHAR_LIMIT
        for page in pages:
            if remaining_chars <= 0:
                break

            payload = page.model_dump(by_alias=True)
            raw_segments = payload.get("segments") if isinstance(payload.get("segments"), list) else []
            segments_payload: list[dict[str, Any]] = []
            if raw_segments:
                for raw_segment in raw_segments:
                    if remaining_chars <= 0:
                        break
                    if len(segments_payload) >= READING_PREVIEW_MAX_SEGMENTS_PER_PAGE:
                        break
                    if not isinstance(raw_segment, dict):
                        continue
                    text_value = raw_segment.get("text")
                    max_chars = min(READING_PREVIEW_SEGMENT_CHAR_LIMIT, remaining_chars)
                    truncated_text = self._truncate_value(text_value, max_chars)
                    if not truncated_text:
                        continue
                    segment_entry = dict(raw_segment)
                    segment_entry["text"] = truncated_text
                    segment_entry["chars"] = len(truncated_text)
                    segments_payload.append(segment_entry)
                    remaining_chars = max(0, remaining_chars - len(truncated_text))
                payload["segments"] = segments_payload
            else:
                payload["segments"] = []

            if segments_payload:
                payload.pop("text", None)
            else:
                max_chars = min(READING_PREVIEW_TEXT_CHAR_LIMIT, remaining_chars)
                truncated_page_text = self._truncate_value(payload.get("text"), max_chars)
                if truncated_page_text:
                    payload["text"] = truncated_page_text
                    remaining_chars = max(0, remaining_chars - len(truncated_page_text))
                else:
                    payload.pop("text", None)

            html_value = payload.get("html")
            if html_value:
                truncated_html = self._truncate_value(html_value, READING_PREVIEW_HTML_CHAR_LIMIT)
                if truncated_html:
                    payload["html"] = truncated_html
                    remaining_chars = max(0, remaining_chars - len(truncated_html))
                else:
                    payload.pop("html", None)

            images_payload: list[dict[str, Any]] = []
            for image in page.images:
                if len(images_payload) >= READING_PREVIEW_MAX_IMAGES_PER_PAGE:
                    break
                source_url = getattr(image, "url", None)
                file_id = getattr(image, "file_id", None)
                image_entry: dict[str, Any] = {}
                if file_id:
                    image_entry["url"] = self._build_download_url(request, file_id)
                    if source_url:
                        image_entry["source"] = source_url
                elif source_url:
                    image_entry["url"] = source_url
                    image_entry["source"] = source_url
                else:
                    continue
                caption = getattr(image, "caption", None)
                if caption:
                    truncated_caption = self._truncate_value(caption, 240)
                    if truncated_caption:
                        image_entry["caption"] = truncated_caption
                images_payload.append(image_entry)
            payload["images"] = images_payload
            payload["segmentCount"] = len(segments_payload)
            payload["imageCount"] = len(images_payload)

            serialized.append(self._json_safe(payload))
        return serialized

    def collect_reading_items(self, snippets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for snippet in snippets:
            reading = snippet.get("reading")
            if not isinstance(reading, dict):
                continue
            pages = reading.get("pages")
            if not pages:
                continue
            entry = {
                "id": snippet.get("id"),
                "name": snippet.get("name"),
                "source": snippet.get("source"),
                **{k: v for k, v in reading.items() if k != "pages"},
                "pages": pages,
            }
            items.append(self._json_safe(entry))
            if len(items) >= 3:
                break
        return items

    async def build_reading_preview(
        self,
        request: Request,
        mongo_client: MongoClient,
        project: str | None,
        doc: Document,
        *,
        limit: int = READING_PREVIEW_LIMIT,
    ) -> dict[str, Any] | None:
        project_name = (doc.project or project or "").strip()
        if not project_name:
            return None

        reading_collection = getattr(request.state, "reading_collection", self._reading_collection)

        doc_order = None
        if doc.url:
            try:
                page_matches = await mongo_client.get_reading_pages(
                    reading_collection,
                    project_name,
                    limit=1,
                    offset=0,
                    url=doc.url,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "knowledge_reading_page_lookup_failed",
                    project=project_name,
                    url=doc.url,
                    error=str(exc),
                )
                page_matches = []
            if page_matches:
                doc_order = page_matches[0].order

        try:
            total_pages = await mongo_client.count_reading_pages(reading_collection, project_name)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "knowledge_reading_total_failed",
                project=project_name,
                error=str(exc),
            )
            total_pages = 0

        if total_pages <= 0 and doc_order is None:
            return None

        offset = 0
        if isinstance(doc_order, int) and doc_order > 0:
            offset = max(0, doc_order - 1)
            if total_pages:
                offset = min(offset, max(0, total_pages - limit))
        try:
            pages = await mongo_client.get_reading_pages(
                reading_collection,
                project_name,
                limit=limit,
                offset=offset,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "knowledge_reading_preview_failed",
                project=project_name,
                offset=offset,
                error=str(exc),
            )
            pages = []

        if not pages:
            return None

        serialized_pages = self._serialize_pages(request, pages)
        has_more = total_pages > offset + len(serialized_pages)
        initial_index = 0
        if isinstance(doc_order, int) and doc_order > 0:
            initial_index = max(0, min(len(serialized_pages) - 1, doc_order - 1 - offset))

        preview = {
            "pages": serialized_pages,
            "project": project_name,
            "total": total_pages,
            "has_more": has_more,
            "startOffset": offset,
            "initialIndex": initial_index,
            "initialUrl": doc.url,
        }
        return self._json_safe(preview)

    async def get_pages(
        self,
        request: Request,
        mongo_client: MongoClient,
        project: str | None,
        *,
        limit: int,
        offset: int,
        url: str | None,
        include_html: bool | None,
    ) -> dict[str, Any]:
        project_name = self._normalize_project(project)
        if not project_name:
            raise HTTPException(status_code=400, detail="project_required")

        safe_limit = max(1, min(int(limit), READING_PAGE_MAX_LIMIT))
        safe_offset = max(0, int(offset))
        include_html_flag = bool(include_html) if include_html is not None else False

        collection = getattr(request.state, "reading_collection", self._reading_collection)
        pages = await mongo_client.get_reading_pages(
            collection,
            project_name,
            limit=safe_limit,
            offset=safe_offset,
            url=url,
        )

        if not include_html_flag:
            for page in pages:
                page.html = None

        if url:
            total = 1 if pages else 0
        else:
            total = await mongo_client.count_reading_pages(collection, project_name)

        has_more = safe_offset + len(pages) < total

        return {
            "pages": pages,
            "total": total,
            "limit": safe_limit,
            "offset": safe_offset,
            "has_more": has_more,
        }
