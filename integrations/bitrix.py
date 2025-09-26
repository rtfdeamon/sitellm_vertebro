"""Helpers for interacting with Bitrix24 webhooks."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class BitrixError(RuntimeError):
    """Raised when the Bitrix API returns an error."""


async def call_bitrix_webhook(
    base_url: str,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Call Bitrix webhook ``method`` with ``params`` and return parsed JSON.

    Parameters
    ----------
    base_url:
        Base webhook URL created inside the Bitrix portal.
    method:
        REST method name, e.g. ``crm.lead.get``.
    params:
        Optional payload forwarded as JSON body.
    timeout:
        Request timeout in seconds.
    """

    cleaned_method = (method or "").strip().strip("/")
    if not cleaned_method:
        raise ValueError("Bitrix method is required")

    cleaned_base = (base_url or "").strip()
    if not cleaned_base:
        raise ValueError("Bitrix webhook URL is required")

    if not cleaned_base.endswith("/"):
        cleaned_base = f"{cleaned_base}/"
    url = f"{cleaned_base}{cleaned_method}"
    if not url.endswith(".json"):
        url = f"{url}.json"

    payload = params or {}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:  # pragma: no cover - network dependent
        logger.warning(
            "bitrix_http_error",
            url=url,
            status=exc.response.status_code,
            text=exc.response.text,
        )
        raise BitrixError(f"Bitrix HTTP error: {exc.response.status_code}") from exc
    except httpx.RequestError as exc:  # pragma: no cover - network dependent
        logger.warning("bitrix_request_failed", url=url, error=str(exc))
        raise BitrixError("Bitrix request failed") from exc

    try:
        data: dict[str, Any] = response.json()
    except ValueError as exc:  # pragma: no cover - malformed payload
        logger.warning("bitrix_invalid_json", url=url, error=str(exc))
        raise BitrixError("Bitrix returned invalid JSON") from exc

    if isinstance(data, dict) and data.get("error"):
        logger.info(
            "bitrix_error_response",
            url=url,
            error=data.get("error"),
            description=data.get("error_description"),
        )
        raise BitrixError(data.get("error_description") or data.get("error") or "Bitrix error")

    return data
