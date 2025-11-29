"""Web utilities for scraping and prompt generation."""

import re
import urllib.parse as urlparse
import httpx
from bs4 import BeautifulSoup
from observability.logging import get_logger
from backend.projects.constants import (
    PROMPT_SAMPLE_CHAR_LIMIT,
    PROMPT_RESPONSE_CHAR_LIMIT,
    PROMPT_FETCH_HEADERS,
    PROMPT_ROLE_TEMPLATES,
    DEFAULT_PROMPT_ROLE,
)

logger = get_logger(__name__)


def normalize_source_url(raw: str) -> str:
    candidate = (raw or "").strip()
    if not candidate:
        raise ValueError("URL is required")
    if not urlparse.urlsplit(candidate).scheme:
        candidate = f"https://{candidate}"
    parsed = urlparse.urlsplit(candidate)
    if not parsed.netloc:
        raise ValueError("Invalid URL")
    path = parsed.path or "/"
    return urlparse.urlunsplit((parsed.scheme or "https", parsed.netloc, path, parsed.query, ""))


def extract_page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template", "svg"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    combined = " ".join(lines)
    if len(combined) > PROMPT_SAMPLE_CHAR_LIMIT:
        return combined[:PROMPT_SAMPLE_CHAR_LIMIT]
    return combined


def describe_prompt_fetch_error(status_code: int) -> str:
    if status_code == 401:
        return "URL требует авторизацию"
    if status_code == 403:
        return "Доступ к URL запрещён"
    if status_code == 404:
        return "Страница не найдена по указанному URL"
    if status_code == 405:
        return "Сайт запретил загрузку страницы (method not allowed)"
    if status_code >= 500:
        return "Сайт вернул внутреннюю ошибку"
    return "Не удалось загрузить страницу"


async def download_page_text(url: str) -> str:
    parsed = urlparse.urlsplit(url)
    path = parsed.path or "/"
    normalized = urlparse.urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, ""))

    candidates: list[str] = []
    seen: set[str] = set()

    def add_candidate(candidate: str) -> None:
        if candidate and candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)

    add_candidate(normalized)

    base_candidate = urlparse.urlunsplit((parsed.scheme, parsed.netloc, "/", "", ""))
    if normalized != base_candidate:
        add_candidate(base_candidate)

    if parsed.scheme.lower() == "https":
        http_path_candidate = urlparse.urlunsplit(("http", parsed.netloc, path, parsed.query, ""))
        add_candidate(http_path_candidate)
        http_base_candidate = urlparse.urlunsplit(("http", parsed.netloc, "/", "", ""))
        add_candidate(http_base_candidate)

    response: httpx.Response | None = None
    last_status_error: httpx.HTTPStatusError | None = None
    last_request_error: httpx.RequestError | None = None

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=PROMPT_FETCH_HEADERS) as client:
        for candidate in candidates:
            try:
                fetched = await client.get(candidate)
                fetched.raise_for_status()
            except httpx.HTTPStatusError as exc:
                last_status_error = exc
                logger.warning(
                    "prompt_page_fetch_http_error",
                    original_url=normalized,
                    attempted_url=candidate,
                    status=exc.response.status_code,
                )
                continue
            except httpx.RequestError as exc:
                last_request_error = exc
                logger.warning(
                    "prompt_page_fetch_request_error",
                    original_url=normalized,
                    attempted_url=candidate,
                    error=str(exc),
                )
                continue
            else:
                if candidate != normalized:
                    logger.info(
                        "prompt_page_fetch_fallback_used",
                        original_url=normalized,
                        resolved_url=candidate,
                    )
                response = fetched
                break

    if response is None:
        if last_status_error is not None:
            status_code = last_status_error.response.status_code
            detail_msg = describe_prompt_fetch_error(status_code)
            raise httpx.HTTPStatusError(detail_msg, request=last_status_error.request, response=last_status_error.response)
        if last_request_error is not None:
            raise httpx.RequestError(f"Ошибка соединения: {last_request_error}", request=last_request_error.request)
        raise httpx.RequestError("Не удалось загрузить страницу", request=None)

    return extract_page_text(response.text)


def summarize_snippets(text: str, *, limit: int = 5) -> list[str]:
    chunks = re.split(r"(?<=[.!?…])\s+", text)
    selections: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        cleaned = chunk.strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        if len(cleaned) < 25:
            continue
        selections.append(cleaned)
        if len(selections) >= limit:
            break
    if not selections and text:
        preview = re.sub(r"\s+", " ", text).strip()
        if preview:
            selections.append(preview[:240])
    return selections


def build_prompt_fallback(role_label: str, url: str, page_text: str) -> str | None:
    snippet_list = summarize_snippets(page_text, limit=6)
    if not snippet_list:
        return None
    bullets = "\n".join(f"- {item}" for item in snippet_list)
    guidance = (
        f"Ты выступаешь в роли {role_label} компании и общаешься на русском языке. "
        "Держи тёплый, профессиональный тон и помогай пользователю находить ответы.\n"
        f"Используй сведения с сайта {url}. Если в запросе нет данных из списка, объясни, что информации нет, и предложи способы уточнить вопрос.\n"
        "Основные факты о компании:\n"
        f"{bullets}\n\n"
        "Отвечай кратко и по делу, по возможности добавляй конкретные детали и призывы к действию, оставайся внимательным к контексту пользователя."
    )
    return guidance[: PROMPT_RESPONSE_CHAR_LIMIT]


def build_prompt_from_role(role: str, url: str, page_text: str) -> tuple[str, str, str]:
    role_key = (role or DEFAULT_PROMPT_ROLE).strip().lower() or DEFAULT_PROMPT_ROLE
    role_meta = PROMPT_ROLE_TEMPLATES.get(role_key, PROMPT_ROLE_TEMPLATES[DEFAULT_PROMPT_ROLE])
    label = role_meta["label"]
    instruction = role_meta["instruction"]

    snippet_list = summarize_snippets(page_text, limit=10)
    snippet_block = "\n".join(f"- {s}" for s in snippet_list)

    # If no snippets, try fallback
    if not snippet_block:
        fallback = build_prompt_fallback(label, url, page_text)
        if fallback:
            return fallback, role_key, label
        # If fallback also empty (empty page text), return minimal
        return (
            f"Ты — {label}. Используй информацию с сайта {url}, но сейчас данных нет. "
            "Отвечай вежливо и предлагай связаться с менеджером.",
            role_key,
            label,
        )

    body = (
        f"Сформируй системный промт для LLM, который будет отвечать на вопросы посетителей сайта.\n"
        f"Инструкция по стилю и роли:\n{instruction}\n\n"
        f"URL страницы: {url}\n"
        f"Роль ассистента: {label}.\n\n"
        "Контент главной страницы (усечён до ключевых фрагментов):\n"
        f"{snippet_block}\n\n"
        "Верни только готовый системный промт на русском языке без пояснений и служебных префиксов."
    )
    return body, role_key, label
