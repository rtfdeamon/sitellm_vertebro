"""Unit tests for Email MCP connector."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import Tool

from connectors.email.server import app, get_client, list_tools, call_tool, list_resources, read_resource
from connectors.email.client import MailClient


@pytest.fixture
def mock_mail_client():
    with patch("connectors.email.server._client") as mock:
        client = MagicMock(spec=MailClient)
        client.send_email = AsyncMock(return_value="msg-123")
        client.fetch_recent = AsyncMock(return_value=[
            {"subject": "Test", "from": "sender@example.com", "date": "2023-01-01", "id": "1"}
        ])
        client.get_settings_info = MagicMock(return_value={
            "imap_host": "imap.test",
            "password": "***",
            "status": "configured"
        })
        # Reset the global client in server module to use our mock
        with patch("connectors.email.server.get_client", return_value=client):
            yield client


@pytest.mark.asyncio
async def test_list_tools():
    """Test that available tools are listed correctly."""
    tools = await list_tools()
    assert len(tools) == 2
    tool_names = {t.name for t in tools}
    assert "send_email" in tool_names
    assert "fetch_recent" in tool_names


@pytest.mark.asyncio
async def test_call_tool_send_email(mock_mail_client):
    """Test sending an email via the tool."""
    args = {
        "to": ["test@example.com"],
        "subject": "Hello",
        "body": "World"
    }
    
    result = await call_tool("send_email", args)
    
    assert len(result) == 1
    assert result[0].type == "text"
    content = json.loads(result[0].text)
    assert content["status"] == "sent"
    assert content["message_id"] == "msg-123"
    
    mock_mail_client.send_email.assert_called_once_with(
        to=["test@example.com"],
        subject="Hello",
        body="World",
        cc=None,
        bcc=None,
        reply_to=None
    )


@pytest.mark.asyncio
async def test_call_tool_fetch_recent(mock_mail_client):
    """Test fetching recent emails via the tool."""
    args = {"limit": 3, "unseen_only": True}
    
    result = await call_tool("fetch_recent", args)
    
    assert len(result) == 1
    content = json.loads(result[0].text)
    assert content["count"] == 1
    assert content["messages"][0]["subject"] == "Test"
    
    mock_mail_client.fetch_recent.assert_called_once_with(
        limit=3,
        unseen_only=True
    )


@pytest.mark.asyncio
async def test_list_resources():
    """Test that available resources are listed correctly."""
    resources = await list_resources()
    assert len(resources) == 1
    assert str(resources[0].uri) == "email://settings/info"
    assert resources[0].name == "Email Configuration"


@pytest.mark.asyncio
async def test_read_resource(mock_mail_client):
    """Test reading the settings resource."""
    content = await read_resource("email://settings/info")
    
    data = json.loads(content)
    assert data["imap_host"] == "imap.test"
    assert data["password"] == "***"
    assert data["status"] == "configured"
