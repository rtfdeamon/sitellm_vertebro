"""Email MCP server implementation."""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.types import Resource, Tool, TextContent

from .client import MailClient

# Initialize MCP server
app = Server("email-connector")

# Global client instance (will be initialized on first use)
_client: MailClient | None = None


def get_client() -> MailClient:
    """Get or create email client instance."""
    global _client
    if _client is None:
        _client = MailClient()
    return _client


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available email tools."""
    return [
        Tool(
            name="send_email",
            description="Send an email via SMTP",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Recipient email addresses",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject",
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body (plain text)",
                    },
                    "cc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "CC recipients",
                    },
                    "bcc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "BCC recipients",
                    },
                    "reply_to": {
                        "type": "string",
                        "description": "Reply-To address",
                    },
                },
                "required": ["to", "subject", "body"],
            },
        ),
        Tool(
            name="fetch_recent",
            description="Fetch recent messages from IMAP inbox",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of messages to fetch (default: 5)",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "unseen_only": {
                        "type": "boolean",
                        "description": "Only fetch unread messages (default: false)",
                        "default": False,
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute an email tool."""
    client = get_client()

    if name == "send_email":
        to = arguments.get("to", [])
        subject = arguments.get("subject", "")
        body = arguments.get("body", "")
        cc = arguments.get("cc")
        bcc = arguments.get("bcc")
        reply_to = arguments.get("reply_to")

        if not to:
            raise ValueError("'to' parameter is required and must be non-empty")

        message_id = await client.send_email(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
        )

        result = {
            "status": "sent",
            "message_id": message_id,
            "recipients": len(to),
        }

        return [
            TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2),
            )
        ]

    elif name == "fetch_recent":
        limit = arguments.get("limit", 5)
        unseen_only = arguments.get("unseen_only", False)

        messages = await client.fetch_recent(
            limit=limit,
            unseen_only=unseen_only,
        )

        result = {
            "count": len(messages),
            "unseen_only": unseen_only,
            "messages": messages,
        }

        return [
            TextContent(
                type="text",
                text=json.dumps(result, ensure_ascii=False, indent=2),
            )
        ]

    else:
        raise ValueError(f"Unknown tool: {name}")


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available email resources."""
    return [
        Resource(
            uri="email://settings/info",
            name="Email Configuration",
            mimeType="application/json",
            description="Information about configured email settings",
        ),
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read an email resource."""
    if uri != "email://settings/info":
        raise ValueError(f"Unknown resource: {uri}")

    client = get_client()
    info = client.get_settings_info()

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
