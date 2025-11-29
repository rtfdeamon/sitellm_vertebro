"""Email client wrapper for MCP connector."""

from __future__ import annotations

import os
from typing import Sequence

from integrations.mail import (
    MailMessagePayload,
    MailSettings,
    fetch_recent_messages,
    send_mail,
)


class MailClient:
    """Client for email operations via SMTP and IMAP."""

    def __init__(
        self,
        *,
        imap_host: str | None = None,
        imap_port: int | None = None,
        imap_ssl: bool = True,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_tls: bool = True,
        username: str | None = None,
        password: str | None = None,
        sender: str | None = None,
        inbox: str = "INBOX",
    ) -> None:
        """Initialize email client.

        Parameters
        ----------
        imap_host:
            IMAP server hostname. Reads from MAIL_IMAP_HOST if not provided.
        imap_port:
            IMAP server port. Reads from MAIL_IMAP_PORT if not provided.
        imap_ssl:
            Use SSL for IMAP connection.
        smtp_host:
            SMTP server hostname. Reads from MAIL_SMTP_HOST if not provided.
        smtp_port:
            SMTP server port. Reads from MAIL_SMTP_PORT if not provided.
        smtp_tls:
            Use TLS for SMTP connection.
        username:
            Email account username. Reads from MAIL_USERNAME if not provided.
        password:
            Email account password. Reads from MAIL_PASSWORD if not provided.
        sender:
            Sender email address. Reads from MAIL_FROM if not provided.
        inbox:
            IMAP inbox folder name.
        """
        self.settings = MailSettings(
            imap_host=imap_host or os.getenv("MAIL_IMAP_HOST", ""),
            imap_port=imap_port or int(os.getenv("MAIL_IMAP_PORT") or (993 if imap_ssl else 143)),
            imap_ssl=imap_ssl,
            smtp_host=smtp_host or os.getenv("MAIL_SMTP_HOST", ""),
            smtp_port=smtp_port or int(os.getenv("MAIL_SMTP_PORT") or (587 if smtp_tls else 25)),
            smtp_tls=smtp_tls,
            username=username or os.getenv("MAIL_USERNAME", ""),
            password=password or os.getenv("MAIL_PASSWORD", ""),
            sender=sender or os.getenv("MAIL_FROM", ""),
            inbox=inbox,
        )

        # Validate required settings
        if not all([
            self.settings.imap_host,
            self.settings.smtp_host,
            self.settings.username,
            self.settings.password,
            self.settings.sender,
        ]):
            raise ValueError("All email settings (hosts, username, password, sender) are required")

    async def send_email(
        self,
        to: Sequence[str],
        subject: str,
        body: str,
        *,
        cc: Sequence[str] | None = None,
        bcc: Sequence[str] | None = None,
        reply_to: str | None = None,
    ) -> str | None:
        """Send an email.

        Parameters
        ----------
        to:
            Recipient email addresses.
        subject:
            Email subject.
        body:
            Email body (plain text).
        cc:
            CC recipients.
        bcc:
            BCC recipients.
        reply_to:
            Reply-To address.

        Returns
        -------
        str | None
            Message ID of sent email.
        """
        payload = MailMessagePayload(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
        )
        result = await send_mail(self.settings, payload)
        return result.message_id

    async def fetch_recent(
        self,
        *,
        limit: int = 5,
        unseen_only: bool = False,
    ) -> list[dict[str, str | None]]:
        """Fetch recent messages from inbox.

        Parameters
        ----------
        limit:
            Maximum number of messages to fetch.
        unseen_only:
            Only fetch unseen (unread) messages.

        Returns
        -------
        list[dict]
            List of message metadata dicts with keys: subject, from, date, id.
        """
        return await fetch_recent_messages(
            self.settings,
            limit=limit,
            unseen_only=unseen_only,
        )

    def get_settings_info(self) -> dict[str, str | int | bool]:
        """Return sanitized settings information.

        Returns
        -------
        dict
            Settings with password masked.
        """
        return {
            "imap_host": self.settings.imap_host,
            "imap_port": self.settings.imap_port,
            "imap_ssl": self.settings.imap_ssl,
            "smtp_host": self.settings.smtp_host,
            "smtp_port": self.settings.smtp_port,
            "smtp_tls": self.settings.smtp_tls,
            "username": self.settings.username,
            "password": "***",
            "sender": self.settings.sender,
            "inbox": self.settings.inbox,
            "status": "configured",
        }
