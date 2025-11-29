"""Bitrix24 MCP server implementation."""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.types import Resource, Tool, TextContent

from .client import BitrixClient

# Initialize MCP server
app = Server("bitrix24-connector")

# Global client instance (will be initialized on first use)
_client: BitrixClient | None = None


def get_client() -> BitrixClient:
    """Get or create Bitrix24 client instance."""
    global _client
    if _client is None:
        _client = BitrixClient()
    return _client


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Bitrix24 tools."""
    return [
        Tool(
            name="call_method",
            description="Execute a Bitrix24 REST API method",
            inputSchema={
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "REST method name (e.g., 'crm.lead.list', 'crm.contact.get')",
                    },
                    "params": {
                        "type": "object",
                        "description": "Optional parameters for the method",
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Request timeout in seconds (default: 10.0)",
                        "default": 10.0,
                    },
                },
                "required": ["method"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a Bitrix24 tool."""
    if name != "call_method":
        raise ValueError(f"Unknown tool: {name}")

    client = get_client()
    method = arguments.get("method")
    params = arguments.get("params")
    timeout = arguments.get("timeout", 10.0)

    if not method:
        raise ValueError("method parameter is required")

    result = await client.call_method(
        method=method,
        params=params,
        timeout=timeout,
    )

    return [
        TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2),
        )
    ]


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available Bitrix24 resources."""
    return [
        Resource(
            uri="bitrix24://webhook/info",
            name="Webhook Configuration",
            mimeType="application/json",
            description="Information about configured Bitrix24 webhook",
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a Bitrix24 resource."""
    if uri != "bitrix24://webhook/info":
        raise ValueError(f"Unknown resource: {uri}")

    client = get_client()
    info = client.get_webhook_info()

    return json.dumps(info, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )

    asyncio.run(main())
