# Email MCP Connector

Model Context Protocol server for email operations via SMTP and IMAP.

## Overview

This connector exposes email functionality via the Model Context Protocol, allowing LLMs to send emails and fetch messages from an inbox.

## Features

- **Tools**: 
  - Send emails via SMTP
  - Fetch recent messages from IMAP inbox
- **Resources**: Query email configuration

## Installation

1. Install dependencies:
   ```bash
   pip install mcp
   ```

2. Set up environment variables:
   ```bash
   export MAIL_IMAP_HOST="imap.example.com"
   export MAIL_IMAP_PORT="993"
   export MAIL_SMTP_HOST="smtp.example.com"
   export MAIL_SMTP_PORT="587"
   export MAIL_USERNAME="your-email@example.com"
   export MAIL_PASSWORD="your-password"
   export MAIL_FROM="your-email@example.com"
   ```

## Configuration

### Environment Variables

Required:
- `MAIL_IMAP_HOST`: IMAP server hostname
- `MAIL_SMTP_HOST`: SMTP server hostname
- `MAIL_USERNAME`: Email account username
- `MAIL_PASSWORD`: Email account password
- `MAIL_FROM`: Sender email address

Optional:
- `MAIL_IMAP_PORT`: IMAP port (default: 993 for SSL, 143 otherwise)
- `MAIL_SMTP_PORT`: SMTP port (default: 587 for TLS, 25 otherwise)

### Common Email Providers

#### Gmail
```bash
export MAIL_IMAP_HOST="imap.gmail.com"
export MAIL_SMTP_HOST="smtp.gmail.com"
export MAIL_IMAP_PORT="993"
export MAIL_SMTP_PORT="587"
```
**Note:** For Gmail, you need to use an App Password, not your regular password.

#### Outlook/Hotmail
```bash
export MAIL_IMAP_HOST="outlook.office365.com"
export MAIL_SMTP_HOST="smtp.office365.com"
export MAIL_IMAP_PORT="993"
export MAIL_SMTP_PORT="587"
```

#### Yandex
```bash
export MAIL_IMAP_HOST="imap.yandex.ru"
export MAIL_SMTP_HOST="smtp.yandex.ru"
export MAIL_IMAP_PORT="993"
export MAIL_SMTP_PORT="587"
```

## Usage

### Running the Server

```bash
python -m connectors.email.server
```

### Available Tools

#### `send_email`

Send an email via SMTP.

**Parameters:**
- `to` (array of strings, required): Recipient email addresses
- `subject` (string, required): Email subject
- `body` (string, required): Email body (plain text)
- `cc` (array of strings, optional): CC recipients
- `bcc` (array of strings, optional): BCC recipients
- `reply_to` (string, optional): Reply-To address

**Example:**
```json
{
  "to": ["recipient@example.com"],
  "subject": "Test Email",
  "body": "This is a test email sent via MCP connector.",
  "cc": ["cc@example.com"]
}
```

#### `fetch_recent`

Fetch recent messages from IMAP inbox.

**Parameters:**
- `limit` (integer, optional): Maximum number of messages to fetch (default: 5, max: 50)
- `unseen_only` (boolean, optional): Only fetch unread messages (default: false)

**Example:**
```json
{
  "limit": 10,
  "unseen_only": true
}
```

### Available Resources

#### `email://settings/info`

Returns information about the configured email settings (with password masked).

## Security

- **Never commit passwords** to version control
- Use environment variables or secure secret management
- The connector automatically masks passwords when exposing configuration
- Consider using app-specific passwords for services that support them (e.g., Gmail)
- Enable 2FA on your email account for additional security

## Troubleshooting

### Authentication Errors

- **Gmail**: Create an App Password in your Google Account settings
- **Outlook**: Ensure "SMTP AUTH" is enabled in mailbox settings
- **Other providers**: Check if you need to enable IMAP/SMTP access

### Connection Errors

- Verify firewall settings allow outbound connections to SMTP/IMAP ports
- Check that the host and port values are correct
- Some networks block email ports - try a different network if issues persist

### SSL/TLS Issues

- Most modern mail servers require SSL (IMAP) or TLS (SMTP)
- If you need to disable SSL/TLS, modify the client initialization in code
