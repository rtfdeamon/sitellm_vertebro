"""Mail connectors for IMAP/SMTP used by the admin interface."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import formatdate, make_msgid, parsedate_to_datetime
import imaplib
import smtplib
import ssl
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:  # pragma: no cover
    from models import Project


__all__ = [
    "MailConnectorError",
    "MailSettings",
    "MailMessagePayload",
    "MailSendResult",
    "fetch_recent_messages",
    "project_mail_settings",
    "send_mail",
    "summarize_messages",
]


class MailConnectorError(RuntimeError):
    """Raised when mail operations cannot be completed."""


@dataclass(slots=True)
class MailSettings:
    username: str
    password: str
    sender: str
    imap_host: str
    imap_port: int
    imap_ssl: bool
    smtp_host: str
    smtp_port: int
    smtp_tls: bool
    smtp_ssl: bool
    signature: str | None = None
    inbox: str = "INBOX"
    timeout: float = 30.0


@dataclass(slots=True)
class MailMessagePayload:
    to: list[str]
    cc: list[str]
    bcc: list[str]
    subject: str
    body: str
    reply_to: str | None = None
    in_reply_to: str | None = None


@dataclass(slots=True)
class MailSendResult:
    message_id: str


@dataclass(slots=True)
class MailMessageSummary:
    subject: str
    sender: str
    date: str
    snippet: str


def _clean_addresses(addresses: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in addresses:
        if not raw:
            continue
        addr = raw.strip()
        if addr:
            cleaned.append(addr)
    return cleaned


def _decode_header_value(value: str | None) -> str:
    if not value:
        return ""
    try:
        decoded = make_header(decode_header(value))
        return str(decoded)
    except Exception:  # noqa: BLE001 - best-effort decoding
        return value


def _extract_plain_text(message) -> str:
    if message.is_multipart():
        for part in message.walk():
            ctype = part.get_content_type()
            disp = part.get_content_disposition()
            if ctype == "text/plain" and disp != "attachment":
                try:
                    return part.get_content()
                except Exception:  # noqa: BLE001
                    payload = part.get_payload(decode=True)
                    if payload is not None:
                        return payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
        return ""
    try:
        return message.get_content()
    except Exception:  # noqa: BLE001
        payload = message.get_payload(decode=True)
        if payload is None:
            return ""
        return payload.decode(message.get_content_charset() or "utf-8", errors="ignore")


def project_mail_settings(project: "Project") -> MailSettings:
    """Build mail connector settings from project configuration."""

    required_pairs = {
        "mail_username": project.mail_username,
        "mail_password": project.mail_password,
        "mail_from": project.mail_from,
        "mail_imap_host": project.mail_imap_host,
        "mail_smtp_host": project.mail_smtp_host,
    }
    missing = [name for name, value in required_pairs.items() if not isinstance(value, str) or not value.strip()]
    if missing:
        raise MailConnectorError(f"missing_fields:{','.join(missing)}")

    try:
        imap_port = int(project.mail_imap_port or 993)
    except Exception as exc:  # noqa: BLE001
        raise MailConnectorError("invalid_imap_port") from exc
    try:
        smtp_port = int(project.mail_smtp_port or (587 if project.mail_smtp_tls else 465))
    except Exception as exc:  # noqa: BLE001
        raise MailConnectorError("invalid_smtp_port") from exc

    imap_ssl = bool(True if project.mail_imap_ssl is None else project.mail_imap_ssl)
    smtp_tls = bool(True if project.mail_smtp_tls is None else project.mail_smtp_tls)
    smtp_ssl = not smtp_tls and smtp_port == 465

    return MailSettings(
        username=project.mail_username.strip(),
        password=project.mail_password,
        sender=project.mail_from.strip(),
        imap_host=project.mail_imap_host.strip(),
        imap_port=imap_port,
        imap_ssl=imap_ssl,
        smtp_host=project.mail_smtp_host.strip(),
        smtp_port=smtp_port,
        smtp_tls=smtp_tls,
        smtp_ssl=smtp_ssl,
        signature=project.mail_signature.strip() if isinstance(project.mail_signature, str) else None,
    )


async def fetch_recent_messages(
    settings: MailSettings,
    *,
    limit: int = 5,
    unseen_only: bool = False,
) -> list[MailMessageSummary]:
    limit = max(1, min(int(limit or 1), 50))
    return await asyncio.to_thread(_fetch_recent_messages_sync, settings, limit, unseen_only)


def _fetch_recent_messages_sync(settings: MailSettings, limit: int, unseen_only: bool) -> list[MailMessageSummary]:
    client: imaplib.IMAP4 | imaplib.IMAP4_SSL
    try:
        if settings.imap_ssl:
            client = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
        else:
            client = imaplib.IMAP4(settings.imap_host, settings.imap_port)
    except Exception as exc:  # noqa: BLE001
        raise MailConnectorError(f"imap_connect_failed:{exc}") from exc

    try:
        client.login(settings.username, settings.password)
    except Exception as exc:  # noqa: BLE001
        raise MailConnectorError(f"imap_auth_failed:{exc}") from exc

    try:
        status, _ = client.select(settings.inbox)
        if status != "OK":
            raise MailConnectorError("imap_select_failed")

        criteria = "UNSEEN" if unseen_only else "ALL"
        status, data = client.search(None, criteria)
        if status != "OK":
            raise MailConnectorError("imap_search_failed")
        raw_ids = data[0].split()
        if not raw_ids:
            return []
        ids = raw_ids[-limit:]
        messages: list[MailMessageSummary] = []
        parser = BytesParser(policy=policy.default)
        for msg_id in reversed(ids):
            status, msg_data = client.fetch(msg_id, "(BODY.PEEK[HEADER] BODY.PEEK[TEXT]<8192)")
            if status != "OK" or not msg_data:
                status, msg_data = client.fetch(msg_id, "(RFC822)")
                if status != "OK" or not msg_data:
                    continue
            raw_bytes = b""
            for part in msg_data:
                if isinstance(part, tuple):
                    raw_bytes += part[1]
            if not raw_bytes:
                continue
            try:
                message = parser.parsebytes(raw_bytes)
            except Exception:  # noqa: BLE001
                continue
            subject = _decode_header_value(message.get("Subject")) or "(без темы)"
            sender = _decode_header_value(message.get("From")) or "—"
            date_value = message.get("Date")
            if date_value:
                try:
                    date_parsed = parsedate_to_datetime(date_value)
                    date_text = date_parsed.isoformat()
                except Exception:  # noqa: BLE001
                    date_text = date_value
            else:
                date_text = ""
            body_text = _extract_plain_text(message)
            snippet = " ".join(body_text.split())[:320]
            messages.append(
                MailMessageSummary(
                    subject=subject,
                    sender=sender,
                    date=date_text,
                    snippet=snippet,
                )
            )
        return messages
    finally:
        try:
            client.logout()
        except Exception:  # noqa: BLE001
            pass


async def send_mail(settings: MailSettings, payload: MailMessagePayload) -> MailSendResult:
    recipients = _clean_addresses(payload.to) + _clean_addresses(payload.cc) + _clean_addresses(payload.bcc)
    if not recipients:
        raise MailConnectorError("recipients_missing")

    message = EmailMessage()
    message["Subject"] = payload.subject or ""
    message["From"] = settings.sender
    message["To"] = ", ".join(_clean_addresses(payload.to))
    if payload.cc:
        message["Cc"] = ", ".join(_clean_addresses(payload.cc))
    if payload.reply_to:
        message["Reply-To"] = payload.reply_to.strip()
    if payload.in_reply_to:
        message["In-Reply-To"] = payload.in_reply_to.strip()
    message["Date"] = formatdate(localtime=True)
    message_id = make_msgid()
    message["Message-ID"] = message_id
    body = payload.body or ""
    message.set_content(body, subtype="plain", charset="utf-8")

    await asyncio.to_thread(_send_message_sync, settings, message, recipients)
    return MailSendResult(message_id=message_id.strip("<>"))


def _send_message_sync(settings: MailSettings, message: EmailMessage, recipients: list[str]) -> None:
    context = ssl.create_default_context()
    try:
        if settings.smtp_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                context=context,
                timeout=settings.timeout,
            ) as server:
                server.login(settings.username, settings.password)
                server.send_message(message, from_addr=settings.sender, to_addrs=recipients)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.timeout) as server:
                server.ehlo()
                if settings.smtp_tls:
                    server.starttls(context=context)
                    server.ehlo()
                server.login(settings.username, settings.password)
                server.send_message(message, from_addr=settings.sender, to_addrs=recipients)
    except Exception as exc:  # noqa: BLE001
        raise MailConnectorError(f"smtp_send_failed:{exc}") from exc


def summarize_messages(messages: list[MailMessageSummary], *, limit: int = 5) -> str:
    if not messages:
        return "Нет новых писем"
    lines = ["Свежие письма:"]
    for idx, item in enumerate(messages[:limit], start=1):
        header = f"{idx}. {item.subject} — {item.sender}"
        if item.date:
            header += f" ({item.date})"
        lines.append(header)
        if item.snippet:
            lines.append(f"    {item.snippet}")
    return "\n".join(lines)
