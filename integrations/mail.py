"""Email connector utilities bridging Telegram instructions to mailbox actions."""

from __future__ import annotations

import asyncio
import contextlib
import imaplib
import smtplib
from dataclasses import dataclass
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default as email_default_policy
from email.utils import formataddr, make_msgid, parseaddr, parsedate_to_datetime
from typing import Iterable, Sequence

import structlog

from models import Project

logger = structlog.get_logger(__name__)


class MailConnectorError(Exception):
    """Raised when the mail connector cannot perform the requested operation."""


@dataclass
class MailSettings:
    """Runtime mail configuration resolved from a project entry."""

    imap_host: str
    imap_port: int
    imap_ssl: bool
    smtp_host: str
    smtp_port: int
    smtp_tls: bool
    username: str
    password: str
    sender: str
    inbox: str = "INBOX"
    signature: str | None = None


@dataclass
class MailActionResult:
    """Structured result describing a performed email action."""

    message_id: str | None = None
    response: str | None = None


@dataclass
class MailMessagePayload:
    """Payload collected from the LLM plan for composing an email."""

    to: Sequence[str]
    subject: str
    body: str
    cc: Sequence[str] | None = None
    bcc: Sequence[str] | None = None
    reply_to: str | None = None
    in_reply_to: str | None = None


def project_mail_settings(project: Project | None) -> MailSettings:
    """Return connector settings for ``project`` or raise if misconfigured."""

    if not project or not getattr(project, "mail_enabled", False):
        raise MailConnectorError("mail_disabled")
    required = (
        project.mail_imap_host,
        project.mail_smtp_host,
        project.mail_username,
        project.mail_password,
        project.mail_from,
    )
    if not all(required):
        raise MailConnectorError("mail_incomplete_settings")
    imap_port = int(project.mail_imap_port or (993 if project.mail_imap_ssl else 143))
    smtp_port = int(project.mail_smtp_port or (587 if project.mail_smtp_tls else 25))
    return MailSettings(
        imap_host=project.mail_imap_host,
        imap_port=imap_port,
        imap_ssl=bool(project.mail_imap_ssl),
        smtp_host=project.mail_smtp_host,
        smtp_port=smtp_port,
        smtp_tls=bool(project.mail_smtp_tls),
        username=project.mail_username,
        password=project.mail_password or "",
        sender=project.mail_from,
        inbox="INBOX",
        signature=project.mail_signature or None,
    )


async def send_mail(settings: MailSettings, payload: MailMessagePayload) -> MailActionResult:
    """Send a plain-text email and return delivery details."""

    to_recipients = normalize_recipients(payload.to)
    if not to_recipients:
        raise MailConnectorError("mail_missing_recipient")
    cc_recipients = normalize_recipients(payload.cc)
    bcc_recipients = normalize_recipients(payload.bcc)

    def _send() -> MailActionResult:
        msg = EmailMessage()
        msg["Subject"] = payload.subject or ""
        msg["From"] = settings.sender
        msg["To"] = ", ".join(to_recipients)
        if cc_recipients:
            msg["Cc"] = ", ".join(cc_recipients)
        if payload.reply_to:
            msg["Reply-To"] = payload.reply_to
        if payload.in_reply_to:
            msg["In-Reply-To"] = payload.in_reply_to
            msg["References"] = payload.in_reply_to
        msg.set_content(payload.body or "")
        msg_id = make_msgid(domain=settings.sender.split("@")[-1])
        msg["Message-ID"] = msg_id
        recipients: list[str] = list(to_recipients)
        recipients.extend(cc_recipients)
        recipients.extend(bcc_recipients)
        server: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            if settings.smtp_tls:
                server = smtplib.SMTP(settings.smtp_host, settings.smtp_port or 587, timeout=20)
                server.starttls()
            elif settings.smtp_port == 465:
                server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port or 465, timeout=20)
            else:
                server = smtplib.SMTP(settings.smtp_host, settings.smtp_port or 25, timeout=20)
            server.login(settings.username, settings.password)
            server.send_message(msg, from_addr=settings.sender, to_addrs=recipients)
        finally:
            if server is not None:
                try:
                    server.quit()
                except Exception:  # noqa: BLE001
                    pass
        logger.info(
            "mail_sent",
            to=to_recipients,
            cc=len(cc_recipients),
            message_id=msg_id,
        )
        return MailActionResult(message_id=msg_id)

    return await asyncio.to_thread(_send)


def _decode_header_value(raw: str | bytes | None) -> str:
    if not raw:
        return ""
    try:
        decoded = make_header(decode_header(raw))
    except Exception:  # noqa: BLE001
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="ignore")
        return str(raw)
    return str(decoded)


async def fetch_recent_messages(
    settings: MailSettings,
    *,
    limit: int = 5,
    unseen_only: bool = False,
) -> list[dict[str, str | None]]:
    """Return lightweight metadata for the newest messages in the inbox."""

    if limit <= 0:
        return []

    def _fetch() -> list[dict[str, str | None]]:
        mailbox = settings.inbox or "INBOX"
        client: imaplib.IMAP4 | imaplib.IMAP4_SSL
        if settings.imap_ssl:
            client = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
        else:
            client = imaplib.IMAP4(settings.imap_host, settings.imap_port)
        try:
            client.login(settings.username, settings.password)
            client.select(mailbox, readonly=True)
            criteria = "(UNSEEN)" if unseen_only else "(ALL)"
            status, data = client.search(None, criteria)
            if status != "OK":
                raise MailConnectorError(f"imap_search_failed:{status}")
            ids = data[0].split()
            if not ids:
                return []
            selected = ids[-limit:]
            results: list[dict[str, str | None]] = []
            for msg_id in reversed(selected):
                status, msg_data = client.fetch(
                    msg_id,
                    "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE MESSAGE-ID FROM)])",
                )
                if status != "OK" or not msg_data:
                    continue
                header_bytes = b""
                for part in msg_data:
                    if isinstance(part, tuple) and part[1]:
                        header_bytes = part[1]
                        break
                if not header_bytes:
                    continue
                parser = BytesParser(policy=email_default_policy)
                message = parser.parsebytes(header_bytes)
                parsed_subject = _decode_header_value(message.get("Subject"))
                parsed_from = message.get("From")
                readable_from = parsed_from
                if parsed_from:
                    name, addr = parseaddr(parsed_from)
                    if addr:
                        readable_from = formataddr((name, addr)) if name or addr else parsed_from
                    else:
                        readable_from = _decode_header_value(parsed_from)
                raw_date = message.get("Date")
                iso_date = None
                if raw_date:
                    with contextlib.suppress(Exception):
                        iso_date = parsedate_to_datetime(raw_date).isoformat()
                results.append(
                    {
                        "subject": parsed_subject or "(без темы)",
                        "from": readable_from,
                        "date": iso_date,
                        "id": _decode_header_value(message.get("Message-ID")),
                    }
                )
            return results
        finally:
            with contextlib.suppress(Exception):
                client.logout()

    return await asyncio.to_thread(_fetch)


def summarize_messages(messages: Iterable[dict[str, str | None]], *, limit: int = 5) -> str:
    """Format messages for consumption by the LLM knowledge stream."""

    lines: list[str] = []
    for idx, item in enumerate(messages, 1):
        subject = item.get("subject") or "(без темы)"
        sender = item.get("from") or "(отправитель не указан)"
        date = item.get("date") or ""
        parts = [f"{idx}. {subject}", sender]
        if date:
            parts.append(date)
        lines.append(" — ".join(parts))
        if idx >= limit:
            break
    return "\n".join(lines)


def normalize_recipients(values: Sequence[str] | None) -> list[str]:
    """Deduplicate and sanitize a list of email recipients."""

    if not values:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for item in values:
        candidate = (item or "").strip()
        if not candidate:
            continue
        lowered = candidate.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(candidate)
    return normalized
