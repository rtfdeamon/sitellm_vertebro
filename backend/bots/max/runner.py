"""MAX bot runner implementation."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import TYPE_CHECKING, Any

import httpx
import structlog

from backend.bots.base import BaseRunner
from backend.bots.utils import format_attachment_preview_lines
from max_bot.config import get_settings as get_max_settings

if TYPE_CHECKING:
    from backend.bots.max.hub import MaxHub

logger = structlog.get_logger(__name__)

_ATTACH_POSITIVE_REPLIES = {
    "да",
    "давай",
    "ок",
    "хочу",
    "конечно",
    "ага",
    "отправь",
    "да пожалуйста",
    "да, отправь",
    "да отправь",
    "yes",
    "yep",
    "sure",
    "send",
    "please send",
}

_ATTACH_NEGATIVE_REPLIES = {
    "нет",
    "не надо",
    "не нужно",
    "пока нет",
    "нет, спасибо",
    "no",
    "not now",
}


class MaxRunner(BaseRunner):
    """Long-polling task for a MAX messenger bot token."""

    def __init__(self, project: str, token: str, hub: MaxHub) -> None:
        super().__init__(project, token, hub)
        self._settings = get_max_settings()

    @property
    def _platform(self) -> str:
        return "max"

    async def _run(self) -> None:
        from tg_bot.client import rag_answer  # Reuse backend client with channel override

        base_url = self._settings.base_url()
        timeout = httpx.Timeout(
            connect=self._settings.request_timeout,
            read=self._settings.request_timeout + self._settings.updates_timeout + 10,
            write=self._settings.request_timeout,
            pool=self._settings.request_timeout,
        )
        params_base = {
            "access_token": self.token,
            "limit": max(1, int(self._settings.updates_limit)),
            "timeout": max(1, int(self._settings.updates_timeout)),
        }
        marker: int | None = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            while True:
                request_params = params_base.copy()
                if marker is not None:
                    request_params["marker"] = marker
                try:
                    response = await client.get(f"{base_url}/updates", params=request_params)
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    detail = exc.response.text
                    message = f"status={status} {detail.strip() or exc!r}"
                    logger.warning("max_updates_failed", project=self.project, status=status, detail=detail)
                    self._hub._errors[self.project] = message
                    await asyncio.sleep(self._settings.idle_sleep_seconds)
                    if status in {401, 403}:
                        # authentication issues - give up until configuration changes
                        await asyncio.sleep(max(15, self._settings.idle_sleep_seconds))
                    continue
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.warning("max_updates_exception", project=self.project, error=str(exc))
                    self._hub._errors[self.project] = str(exc)
                    await asyncio.sleep(self._settings.idle_sleep_seconds)
                    continue

                try:
                    payload = response.json()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("max_updates_decode_failed", project=self.project, error=str(exc))
                    self._hub._errors[self.project] = f"decode_error: {exc}"
                    await asyncio.sleep(self._settings.idle_sleep_seconds)
                    continue

                updates = payload.get("updates") or []
                marker = payload.get("marker", marker)
                if not updates:
                    self._hub._errors.pop(self.project, None)
                    await asyncio.sleep(self._settings.idle_sleep_seconds)
                    continue

                for update in updates:
                    if self._task is None or self._task.cancelled():
                        return
                    try:
                        await self._handle_update(update, client, rag_answer)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("max_update_failed", project=self.project, error=str(exc))
                        self._hub._errors[self.project] = str(exc)
                        await asyncio.sleep(self._settings.idle_sleep_seconds)
                        break
                else:
                    self._hub._errors.pop(self.project, None)

    async def _handle_update(
        self,
        update: dict[str, Any],
        client: httpx.AsyncClient,
        rag_answer_fn: Any,
    ) -> None:
        update_type = str(update.get("update_type") or "").strip().lower()
        if update_type == "message_created":
            await self._handle_message_created(update, client, rag_answer_fn)
        else:
            logger.debug(
                "max_update_ignored",
                project=self.project,
                update_type=update_type,
            )

    async def _handle_message_created(self, update: dict[str, Any], client: httpx.AsyncClient, rag_answer_fn: Any) -> None:
        message = update.get("message") or {}
        sender = message.get("sender") or {}
        if sender.get("is_bot"):
            return
        body = message.get("body") or {}
        text = (body.get("text") or "").strip()
        if not text:
            return

        session_key = self._session_key(message)
        session_id: str | None = None
        if session_key:
            session_uuid = await self._hub.get_or_create_session(self.project, session_key)
            session_id = str(session_uuid)

        recipient = message.get("recipient") or {}
        normalized_text = text.lower()
        if session_key:
            pending = await self._hub.get_pending_attachments(self.project, session_key)
            if pending and normalized_text:
                if normalized_text in _ATTACH_POSITIVE_REPLIES:
                    await self._hub.clear_pending_attachments(self.project, session_key)
                    await self._send_message(
                        client,
                        recipient,
                        {"text": "📎 Отправляю материалы."},
                    )
                    await self._deliver_pending_attachments(
                        client,
                        recipient,
                        pending.get("attachments", []),
                    )
                    return
                if normalized_text in _ATTACH_NEGATIVE_REPLIES:
                    await self._hub.clear_pending_attachments(self.project, session_key)
                    await self._send_message(
                        client,
                        recipient,
                        {"text": "Понял, документы отправлять не буду."},
                    )
                    return
                await self._hub.clear_pending_attachments(self.project, session_key)

        try:
            answer = await rag_answer_fn(
                text,
                project=self.project,
                session_id=session_id,
                channel="max",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("max_answer_failed", project=self.project, error=str(exc))
            self._hub._errors[self.project] = f"answer_error: {exc}"
            return

        response_text = str(answer.get("text") or "").strip()
        attachments = answer.get("attachments") or []
        fallback_blocks: list[str] = []
        attachment_messages: list[dict[str, Any]] = []
        confirm_prompt: str | None = None

        if attachments:
            if session_key:
                await self._hub.set_pending_attachments(
                    self.project,
                    session_key,
                    {"attachments": attachments},
                )
                preview_lines = format_attachment_preview_lines(attachments)
                if preview_lines:
                    preview_block = "\n".join(preview_lines)
                    confirm_prompt = (
                        "📎 Нашёл полезные материалы:\n"
                        f"{preview_block}\n"
                        "Отправить документы? Ответьте «да» или «нет»."
                    )
                else:
                    confirm_prompt = "📎 У меня есть документы по теме. Отправить их? Ответьте «да» или «нет»."
            else:
                async with httpx.AsyncClient(timeout=self._settings.request_timeout) as download_client:
                    prepared, fallbacks = await self._prepare_max_attachments(
                        attachments,
                        client,
                        download_client,
                    )
                    attachment_messages = prepared
                    fallback_blocks.extend(fallbacks)

        if fallback_blocks:
            block = "\n\n".join(fallback_blocks)
            response_text = f"{response_text}\n\n{block}" if response_text else block

        if confirm_prompt:
            response_text = f"{response_text}\n\n{confirm_prompt}" if response_text else confirm_prompt

        response_text = self._clip_text(response_text)

        if response_text:
            await self._send_message(client, recipient, {"text": response_text})

        for item in attachment_messages:
            await self._send_message(client, recipient, item)

    def _session_key(self, message: dict[str, Any]) -> str | None:
        recipient = message.get("recipient") or {}
        chat_id = recipient.get("chat_id")
        if chat_id is not None:
            return f"chat:{chat_id}"
        sender = message.get("sender") or {}
        user_id = sender.get("user_id") or recipient.get("user_id")
        if user_id is not None:
            return f"user:{user_id}"
        return None

    def _clip_text(self, text: str) -> str:
        value = text.strip()
        if len(value) > 3800:
            value = value[:3797].rstrip() + "…"
        return value

    async def _send_message(self, client: httpx.AsyncClient, recipient: dict[str, Any], payload: dict[str, Any]) -> None:
        params: dict[str, Any] = {
            "access_token": self.token,
        }
        chat_id = recipient.get("chat_id")
        user_id = recipient.get("user_id")
        if chat_id is not None:
            params["chat_id"] = chat_id
        if user_id is not None and "chat_id" not in params:
            params["user_id"] = user_id

        body: dict[str, Any] = {}
        text = payload.get("text")
        attachments = payload.get("attachments")
        if text:
            body["text"] = text
            if self._settings.disable_link_preview:
                params["disable_link_preview"] = "true"
        if attachments:
            body["attachments"] = attachments
        if not body:
            return

        base_url = self._settings.base_url()
        try:
            response = await client.post(
                f"{base_url}/messages",
                params=params,
                json=body,
            )
            response.raise_for_status()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("max_send_failed", project=self.project, error=str(exc))
            self._hub._errors[self.project] = f"send_error: {exc}"

    async def _prepare_max_attachments(
        self,
        attachments: list[dict[str, Any]],
        api_client: httpx.AsyncClient,
        download_client: httpx.AsyncClient,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        prepared: list[dict[str, Any]] = []
        fallbacks: list[str] = []
        for idx, attachment in enumerate(attachments, start=1):
            try:
                result = await self._prepare_single_attachment(attachment, api_client, download_client)
            except Exception as exc:  # noqa: BLE001
                logger.warning("max_attachment_prepare_failed", project=self.project, error=str(exc))
                result = None
            if result:
                prepared.append(result)
            else:
                fallback = self._attachment_fallback_text(attachment, idx)
                if fallback:
                    fallbacks.append(fallback)
        return prepared, fallbacks

    async def _prepare_single_attachment(
        self,
        attachment: dict[str, Any],
        api_client: httpx.AsyncClient,
        download_client: httpx.AsyncClient,
    ) -> dict[str, Any] | None:
        from mongo import NotFound

        name = str(attachment.get("name") or attachment.get("title") or "attachment")
        description = attachment.get("description")
        content_type = str(attachment.get("content_type") or "")
        file_bytes: bytes | None = None

        file_id = attachment.get("file_id") or attachment.get("id")
        if file_id:
            try:
                doc_meta, payload = await self._hub._mongo.get_document_with_content(
                    self._hub._mongo.documents_collection,
                    file_id,
                )
                file_bytes = payload
                if not content_type:
                    content_type = str(doc_meta.get("content_type") or "")
            except NotFound:
                file_bytes = None
            except Exception as exc:  # noqa: BLE001
                logger.warning("max_attachment_mongo_failed", project=self.project, error=str(exc))

        if file_bytes is None:
            download_url = attachment.get("download_url") or attachment.get("url")
            if download_url and str(download_url).lower().startswith("http"):
                try:
                    response = await download_client.get(download_url)
                    response.raise_for_status()
                    file_bytes = response.content
                    if not content_type:
                        content_type = str(response.headers.get("content-type") or "")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("max_attachment_download_failed", project=self.project, error=str(exc), url=download_url)
            else:
                return None

        if not file_bytes:
            return None
        if not content_type:
            content_type = "application/octet-stream"

        upload_type = self._detect_upload_type(content_type)
        base_url = self._settings.base_url()
        try:
            upload_resp = await api_client.post(
                f"{base_url}/uploads",
                params={"access_token": self.token, "type": upload_type},
            )
            upload_resp.raise_for_status()
            upload_meta = upload_resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("max_upload_init_failed", project=self.project, error=str(exc))
            return None

        upload_url = upload_meta.get("url")
        initial_token = upload_meta.get("token")
        if not upload_url:
            return None

        try:
            upload_response = await download_client.post(
                upload_url,
                files={"data": (name, file_bytes, content_type or "application/octet-stream")},
            )
            upload_response.raise_for_status()
            try:
                upload_result = upload_response.json()
            except Exception:  # noqa: BLE001
                upload_result = {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("max_upload_failed", project=self.project, error=str(exc), url=upload_url)
            return None

        payload: dict[str, Any] | None = None
        if upload_type in {"video", "audio"}:
            token_value = initial_token or upload_result.get("token")
            if token_value:
                payload = {"token": token_value}
        elif upload_type == "image":
            photos = upload_result.get("photos")
            token_value = upload_result.get("token")
            if photos:
                payload = {"photos": photos}
            elif token_value:
                payload = {"token": token_value}
        else:  # file or other
            token_value = upload_result.get("token")
            if token_value:
                payload = {"token": token_value}

        if not payload:
            logger.warning("max_upload_no_token", project=self.project, type=upload_type)
            return None

        attachment_request = {"type": upload_type, "payload": payload}
        caption = description or name
        message_payload = {"attachments": [attachment_request]}
        if caption:
            message_payload["text"] = self._clip_text(str(caption))
        return message_payload

    def _detect_upload_type(self, content_type: str) -> str:
        lowered = (content_type or "").lower()
        if lowered.startswith("image/"):
            return "image"
        if lowered.startswith("video/"):
            return "video"
        if lowered.startswith("audio/"):
            return "audio"
        return "file"

    def _attachment_fallback_text(self, attachment: dict[str, Any], index: int) -> str | None:
        name = str(attachment.get("name") or attachment.get("title") or f"Документ {index}")
        description = attachment.get("description")
        download = attachment.get("download_url") or attachment.get("url")
        lines = [f"{index}. {name}"]
        if description:
            lines.append(str(description))
        if download:
            lines.append(str(download))
        return "\n".join(lines)

    async def _deliver_pending_attachments(
        self,
        api_client: httpx.AsyncClient,
        recipient: dict[str, Any],
        attachments: list[dict[str, Any]],
    ) -> None:
        if not attachments:
            return

        async with httpx.AsyncClient(timeout=self._settings.request_timeout) as download_client:
            prepared, fallbacks = await self._prepare_max_attachments(
                attachments,
                api_client,
                download_client,
            )
        for item in prepared:
            await self._send_message(api_client, recipient, item)
        if fallbacks:
            await self._send_message(
                api_client,
                recipient,
                {"text": "\n".join(fallbacks)},
            )
