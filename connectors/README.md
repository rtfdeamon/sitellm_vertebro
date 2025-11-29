# MCP Connectors

This directory contains Model Context Protocol (MCP) servers that expose various integrations as standardized tools and resources for LLM interaction.

## Available Connectors

### Bitrix24 (`connectors/bitrix24/`)

MCP server for Bitrix24 CRM integration. Provides tools to interact with Bitrix24 REST API via webhooks.

**Features:**
- Execute Bitrix24 REST API methods
- Query webhook configuration

See [bitrix24/README.md](bitrix24/README.md) for details.

### Email (`connectors/email/`)

MCP server for email operations via SMTP and IMAP.

**Features:**
- Send emails via SMTP
- Fetch recent messages from IMAP inbox

See [email/README.md](email/README.md) for details.

## Installation

Install the MCP package:

```bash
pip install mcp
```

Or if using uv:

```bash
uv pip install mcp
```

## General Usage

Each connector is a standalone MCP server that can be run independently. Refer to individual connector README files for specific configuration and usage instructions.

## Configuration

Connectors are configured via environment variables or project-specific settings loaded from the database. See individual connector documentation for required configuration parameters.
