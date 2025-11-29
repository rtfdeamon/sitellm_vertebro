"""Unit tests for Bitrix24 MCP connector."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import Tool

from connectors.bitrix24.server import app, get_client, list_tools, call_tool, list_resources, read_resource
from connectors.bitrix24.client import BitrixClient


@pytest.fixture
def mock_bitrix_client():
    with patch("connectors.bitrix24.server._client") as mock:
        client = MagicMock(spec=BitrixClient)
        client.call_method = AsyncMock(return_value={"result": "success"})
        client.get_webhook_info = MagicMock(return_value={
            "webhook_url": "https://bitrix.test/***",
            "status": "configured"
        })
        # Reset the global client in server module to use our mock
        with patch("connectors.bitrix24.server.get_client", return_value=client):
            yield client


@pytest.mark.asyncio
async def test_list_tools():
    """Test that available tools are listed correctly."""
    tools = await list_tools()
    assert len(tools) == 1
    assert tools[0].name == "call_method"


@pytest.mark.asyncio
async def test_call_tool_call_method(mock_bitrix_client):
    """Test calling a Bitrix method via the tool."""
    args = {
        "method": "crm.lead.list",
        "params": {"filter": {"STATUS_ID": "NEW"}},
        "timeout": 5.0
    }
    
    result = await call_tool("call_method", args)
    
    assert len(result) == 1
    assert result[0].type == "text"
    content = json.loads(result[0].text)
    assert content["result"] == "success"
    
    mock_bitrix_client.call_method.assert_called_once_with(
        method="crm.lead.list",
        params={"filter": {"STATUS_ID": "NEW"}},
        timeout=5.0
    )


@pytest.mark.asyncio
async def test_list_resources():
    """Test that available resources are listed correctly."""
    resources = await list_resources()
    assert len(resources) == 1
    assert str(resources[0].uri) == "bitrix24://webhook/info"
    assert resources[0].name == "Webhook Configuration"


@pytest.mark.asyncio
async def test_read_resource(mock_bitrix_client):
    """Test reading the webhook info resource."""
    content = await read_resource("bitrix24://webhook/info")
    
    data = json.loads(content)
    assert "webhook_url" in data
    assert "***" in data["webhook_url"]
    assert data["status"] == "configured"
