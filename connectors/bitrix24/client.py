"""Bitrix24 client wrapper for MCP connector."""

from __future__ import annotations

import os
from typing import Any

from integrations.bitrix import call_bitrix_webhook


class BitrixClient:
    """Client for Bitrix24 webhook API calls."""

    def __init__(self, webhook_url: str | None = None) -> None:
        """Initialize Bitrix24 client.

        Parameters
        ----------
        webhook_url:
            Base webhook URL. If not provided, will read from BITRIX_WEBHOOK_URL
            environment variable.
        """
        self.webhook_url = webhook_url or os.getenv("BITRIX_WEBHOOK_URL", "")
        if not self.webhook_url:
            raise ValueError("Bitrix webhook URL is required")

    async def call_method(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """Call a Bitrix24 REST API method.

        Parameters
        ----------
        method:
            REST method name, e.g. 'crm.lead.list'.
        params:
            Optional parameters to pass to the method.
        timeout:
            Request timeout in seconds.

        Returns
        -------
        dict
            Response data from Bitrix24 API.
        """
        return await call_bitrix_webhook(
            base_url=self.webhook_url,
            method=method,
            params=params,
            timeout=timeout,
        )

    def get_webhook_info(self) -> dict[str, str]:
        """Return sanitized webhook configuration info.

        Returns
        -------
        dict
            Webhook URL with credentials masked.
        """
        # Mask sensitive parts of the webhook URL
        url = self.webhook_url
        if "/" in url:
            parts = url.split("/")
            # Keep domain and mask the rest
            masked = f"{parts[0]}//{parts[2]}/***"
        else:
            masked = "***"

        return {
            "webhook_url": masked,
            "status": "configured",
        }
