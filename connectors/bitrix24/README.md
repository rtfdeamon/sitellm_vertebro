# Bitrix24 MCP Connector

Model Context Protocol server for Bitrix24 CRM integration.

## Overview

This connector exposes Bitrix24 REST API functionality via the Model Context Protocol, allowing LLMs to interact with your Bitrix24 CRM.

## Features

- **Tools**: Execute any Bitrix24 REST API method
- **Resources**: Query webhook configuration

## Installation

1. Install dependencies:
   ```bash
   pip install mcp
   ```

2. Set up environment variables:
   ```bash
   export BITRIX_WEBHOOK_URL="https://your-domain.bitrix24.com/rest/1/your-webhook-key/"
   ```

## Configuration

### Environment Variables

- `BITRIX_WEBHOOK_URL` (required): Your Bitrix24 webhook URL obtained from the Bitrix24 admin panel

### Getting a Webhook URL

1. Log in to your Bitrix24 portal
2. Go to Settings → Developer resources → Other → Inbound webhook
3. Create a webhook with required permissions
4. Copy the generated URL

## Usage

### Running the Server

```bash
python -m connectors.bitrix24.server
```

### Available Tools

#### `call_method`

Execute any Bitrix24 REST API method.

**Parameters:**
- `method` (string, required): REST method name (e.g., `crm.lead.list`, `crm.contact.get`)
- `params` (object, optional): Method parameters
- `timeout` (number, optional): Request timeout in seconds (default: 10.0)

**Example:**
```json
{
  "method": "crm.lead.list",
  "params": {
    "select": ["ID", "TITLE", "NAME"],
    "filter": {"STATUS_ID": "NEW"}
  }
}
```

### Available Resources

#### `bitrix24://webhook/info`

Returns information about the configured webhook (with credentials masked).

## API Reference

See [Bitrix24 REST API Documentation](https://dev.bitrix24.com/rest_help/) for available methods and parameters.

## Common Methods

- `crm.lead.list` - List CRM leads
- `crm.lead.get` - Get lead details
- `crm.lead.add` - Create new lead
- `crm.contact.list` - List contacts
- `crm.deal.list` - List deals
- `tasks.task.list` - List tasks

## Security

- Webhook URLs contain sensitive credentials and should never be committed to version control
- The connector masks webhook credentials when exposing configuration info
- Always use environment variables for configuration
