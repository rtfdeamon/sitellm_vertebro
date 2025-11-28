"""VK bot runner implementation."""

from __future__ import annotations

import asyncio
import random
from contextlib import suppress
from typing import TYPE_CHECKING, Any

import httpx
import structlog

from backend.bots.base import BaseRunner
from backend.bots.utils import format_attachment_preview_lines
from vk_bot.config import get_settings as get_vk_settings

if TYPE_CHECKING:
    from backend.bots.vk.hub import VkHub

logger = structlog.get_logger(__name__)


class VkRunner(BaseRunner):
    """Long-polling task for a VK messenger bot token."""

    def __init__(self, project: str, token: str, hub: VkHub) -> None:
        super().__init__(project, token, hub)
        self._settings = get_vk_settings()
        self._longpoll_key: str | None = None
        self._longpoll_server: str | None = None
        self._longpoll_ts: str | None = None

    @property
    def _platform(self) -> str:
        return "vk"

    async def stop(self) -> None:
        await super().stop()
        self._reset_longpoll()

    def _reset_longpoll(self) -> None:
        self._longpoll_key = None
        self._longpoll_server = None
        self._longpoll_ts = None

    async def _run(self) -> None:
        from tg_bot.client import rag_answer

        timeout = httpx.Timeout(
            connect=self._settings.request_timeout,
            read=self._settings.request_timeout + self._settings.long_poll_wait + 10,
            write=self._settings.request_timeout,
            pool=self._settings.request_timeout,
        )

        async with httpx.AsyncClient(timeout=timeout) as api_client, httpx.AsyncClient(
            timeout=self._settings.request_timeout
        ) as transfer_client:
            while True:
                try:
                    await self._ensure_longpoll(api_client)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.warning("vk_longpoll_init_failed", project=self.project, error=str(exc))
                    self._hub._errors[self.project] = f"longpoll_init: {exc}"
                    await asyncio.sleep(self._settings.retry_delay_seconds)
                    continue

                try:
                    payload = await self._poll_longpoll(api_client)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    logger.warning("vk_longpoll_request_failed", project=self.project, error=str(exc))
                    self._hub._errors[self.project] = f"longpoll: {exc}"
                    await asyncio.sleep(self._settings.retry_delay_seconds)
                    self._reset_longpoll()
                    continue

                if not payload:
                    await asyncio.sleep(self._settings.idle_sleep_seconds)
                    continue

                failed = payload.get("failed")
                if failed:
                    if failed == 1:
                        self._longpoll_ts = payload.get("ts") or self._longpoll_ts
                    elif failed in {2, 3}:
                        self._reset_longpoll()
                    else:
                        logger.debug(
                            "vk_longpoll_failed_code",
                            project=self.project,
                            failed=failed,
                        )
                        await asyncio.sleep(self._settings.retry_delay_seconds)
                    continue

                if payload.get("ts"):
                    self._longpoll_ts = payload.get("ts")

                updates = payload.get("updates") or []
                if not updates:
                    self._hub._errors.pop(self.project, None)
                    continue

                for update in updates:
                    if self._task is None or self._task.cancelled():
                        return
                    try:
                        await self._handle_update(update, api_client, transfer_client, rag_answer)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("vk_update_failed", project=self.project, error=str(exc))
                        self._hub._errors[self.project] = str(exc)
                        await asyncio.sleep(self._settings.retry_delay_seconds)
                        break
                else:
                    self._hub._errors.pop(self.project, None)

    async def _ensure_longpoll(self, client: httpx.AsyncClient) -> None:
        if self._longpoll_key and self._longpoll_server and self._longpoll_ts:
            return
        response = await self._api_call(client, "groups.getLongPollServer")
        key = response.get("key")
        server = response.get("server")
        ts = response.get("ts")
        if not key or not server or not ts:
            raise RuntimeError("invalid long poll payload")
        self._longpoll_key = str(key)
        self._longpoll_server = str(server)
        self._longpoll_ts = str(ts)

    async def _poll_longpoll(self, client: httpx.AsyncClient) -> dict[str, Any] | None:
        if not (self._longpoll_server and self._longpoll_key and self._longpoll_ts):
            return None
        params = {
            "act": "a_check",
            "key": self._longpoll_key,
            "ts": self._longpoll_ts,
            "wait": max(1, int(self._settings.long_poll_wait)),
            "mode": int(self._settings.long_poll_mode),
            "version": int(self._settings.long_poll_version),
        }
        url = self._longpoll_server
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        response = await client.get(url, params=params)
        response.raise_for_status()
        try:
            return response.json()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"invalid long poll response: {exc}") from exc

    async def _handle_update(
        self,
        update: dict[str, Any] | None,
        api_client: httpx.AsyncClient,
        transfer_client: httpx.AsyncClient,
        rag_answer_fn: Any,
    ) -> None:
        if not isinstance(update, dict):
            return
        update_type = str(update.get("type") or "").lower()
        if update_type != "message_new":
            logger.debug(
                "vk_update_ignored",
                project=self.project,
                update_type=update_type,
            )
            return

        obj = update.get("object") or {}
        message = obj.get("message") or {}
        if int(message.get("out") or 0) == 1:
            return

        text = (message.get("text") or "").strip()
        if not text:
            return

        peer_id = message.get("peer_id")
        if peer_id is None:
            return

        session_key = self._session_key(message)
        session_id: str | None = None
        if session_key:
            session_uuid = await self._hub.get_or_create_session(self.project, session_key)
            session_id = str(session_uuid)

        try:
            answer = await rag_answer_fn(
                text,
                project=self.project,
                session_id=session_id,
                channel="vk",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("vk_answer_failed", project=self.project, error=str(exc))
            self._hub._errors[self.project] = f"answer_error: {exc}"
            return

        response_text = str(answer.get("text") or "").strip()
        attachments = answer.get("attachments") or []
        fallback_blocks: list[str] = []
        attachment_handles: list[str] = []
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
                handles, fallbacks = await self._prepare_vk_attachments(
                    attachments,
                    api_client,
                    transfer_client,
                    peer_id,
                )
                attachment_handles.extend(handles)
                fallback_blocks.extend(fallbacks)

        if fallback_blocks:
            block = "\n\n".join(fallback_blocks)
            response_text = f"{response_text}\n\n{block}" if response_text else block

        if confirm_prompt:
            response_text = f"{response_text}\n\n{confirm_prompt}" if response_text else confirm_prompt

        response_text = self._clip_text(response_text)
        if not response_text and not attachment_handles:
            return

        await self._send_message(api_client, peer_id, response_text or None, attachment_handles)

    def _session_key(self, message: dict[str, Any]) -> str | None:
        peer_id = message.get("peer_id")
        try:
            peer = int(peer_id) if peer_id is not None else None
        except (TypeError, ValueError):
            peer = None
        if peer is None:
            return None
        if peer >= 2_000_000_000:
            return f"chat:{peer}"
        from_id = message.get("from_id")
        try:
            sender = int(from_id) if from_id is not None else peer
        except (TypeError, ValueError):
            sender = peer
        return f"user:{sender}"

    def _clip_text(self, text: str) -> str:
        value = text.strip()
        if len(value) > 3900:
            value = value[:3897].rstrip() + "…"
        return value

    async def _send_message(
        self,
        client: httpx.AsyncClient,
        peer_id: int | str,
        text: str | None,
        attachments: list[str],
    ) -> None:
        params: dict[str, Any] = {
            "peer_id": peer_id,
            "random_id": random.randint(1, 2**31 - 1),
        }
        if text:
            params["message"] = text
            if self._settings.disable_link_preview:
                params["dont_parse_links"] = 1
        if attachments:
            params["attachment"] = ",".join(attachments)
        try:
            await self._api_call(client, "messages.send", params, http_method="POST")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("vk_send_failed", project=self.project, error=str(exc))
            self._hub._errors[self.project] = f"send_error: {exc}"

    async def _prepare_vk_attachments(
        self,
        attachments: list[dict[str, Any]],
        api_client: httpx.AsyncClient,
        transfer_client: httpx.AsyncClient,
        peer_id: int | str,
    ) -> tuple[list[str], list[str]]:
        prepared: list[str] = []
        fallbacks: list[str] = []
        for idx, attachment in enumerate(attachments, start=1):
            try:
                handle = await self._prepare_single_attachment(
                    attachment,
                    api_client,
                    transfer_client,
                    peer_id,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning("vk_attachment_prepare_failed", project=self.project, error=str(exc))
                handle = None
            if handle:
                prepared.append(handle)
            else:
                fallback = self._attachment_fallback_text(attachment, idx)
                if fallback:
                    fallbacks.append(fallback)
        return prepared, fallbacks

    async def _prepare_single_attachment(
        self,
        attachment: dict[str, Any],
        api_client: httpx.AsyncClient,
        transfer_client: httpx.AsyncClient,
        peer_id: int | str,
    ) -> str | None:
        from mongo import NotFound

        name = str(attachment.get("name") or attachment.get("title") or "attachment")
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
                logger.warning("vk_attachment_mongo_failed", project=self.project, error=str(exc))

        if file_bytes is None:
            download_url = attachment.get("download_url") or attachment.get("url")
            if download_url and str(download_url).lower().startswith("http"):
                try:
                    response = await transfer_client.get(download_url)
                    response.raise_for_status()
                    file_bytes = response.content
                    if not content_type:
                        content_type = str(response.headers.get("content-type") or "")
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "vk_attachment_download_failed",
                        project=self.project,
                        error=str(exc),
                        url=download_url,
                    )
                    file_bytes = None
            else:
                return None

        if not file_bytes:
            return None

        upload_type = self._detect_upload_type(content_type)

        if upload_type == "photo":
            upload_info = await self._api_call(
                api_client,
                "photos.getMessagesUploadServer",
                params={"peer_id": peer_id},
            )
            upload_url = upload_info.get("upload_url")
            if not upload_url:
                return None
            files = {
                "file": (name, file_bytes, content_type or "image/jpeg"),
            }
            response = await transfer_client.post(upload_url, files=files)
            response.raise_for_status()
            try:
                upload_payload = response.json()
            except Exception as exc:  # noqa: BLE001
                logger.warning("vk_photo_upload_decode_failed", project=self.project, error=str(exc))
                return None

            saved = await self._api_call(
                api_client,
                "photos.saveMessagesPhoto",
                params={
                    "photo": upload_payload.get("photo"),
                    "server": upload_payload.get("server"),
                    "hash": upload_payload.get("hash"),
                },
                http_method="POST",
            )
            photo_info: dict[str, Any] | None
            if isinstance(saved, list) and saved:
                photo_info = saved[0]
            elif isinstance(saved, dict):
                photo_info = saved
            else:
                photo_info = None
            if not isinstance(photo_info, dict):
                return None
            owner_id = photo_info.get("owner_id")
            media_id = photo_info.get("id")
            access_key = photo_info.get("access_key")
            if owner_id is None or media_id is None:
                return None
            handle = f"photo{owner_id}_{media_id}"
            if access_key:
                handle = f"{handle}_{access_key}"
            return handle

        upload_info = await self._api_call(api_client, "docs.getMessagesUploadServer")
        upload_url = upload_info.get("upload_url")
        if not upload_url:
            return None

        files = {
            "file": (name, file_bytes, content_type or "application/octet-stream"),
        }
        response = await transfer_client.post(upload_url, files=files)
        response.raise_for_status()
        try:
            upload_payload = response.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("vk_doc_upload_decode_failed", project=self.project, error=str(exc))
            return None

        file_field = upload_payload.get("file")
        if not file_field:
            return None

        saved = await self._api_call(
            api_client,
            "docs.save",
            params={"file": file_field},
            http_method="POST",
        )
        if isinstance(saved, list) and saved:
            doc_info = saved[0]
            if isinstance(doc_info, dict) and "doc" in doc_info:
                doc_info = doc_info.get("doc")
        elif isinstance(saved, dict) and "doc" in saved:
            doc_info = saved.get("doc")
        else:
            doc_info = saved
        if not isinstance(doc_info, dict):
            return None
        owner_id = doc_info.get("owner_id")
        media_id = doc_info.get("id")
        access_key = doc_info.get("access_key")
        if owner_id is None or media_id is None:
            return None
        handle = f"doc{owner_id}_{media_id}"
        if access_key:
            handle = f"{handle}_{access_key}"
        return handle

    def _detect_upload_type(self, content_type: str) -> str:
        lowered = (content_type or "").lower()
        if lowered.startswith("image/"):
            return "photo"
        return "doc"

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

    async def _api_call(
        self,
        client: httpx.AsyncClient,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        http_method: str = "GET",
    ) -> dict[str, Any]:
        base_url = f"{self._settings.base_url()}/method/{method}"
        query: dict[str, Any] = {
            "access_token": self.token,
            "v": self._settings.api_version,
        }
        if params:
            for key, value in params.items():
                if value is not None:
                    query[key] = value
        response = await client.request(http_method, base_url, params=query)
        response.raise_for_status()
        try:
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"invalid VK response: {exc}") from exc
        if "error" in payload:
            error = payload.get("error", {})
            code = error.get("error_code")
            message = error.get("error_msg")
            raise RuntimeError(f"VK API error {code}: {message}")
        result = payload.get("response")
        if result is None:
            return {}
        return result
