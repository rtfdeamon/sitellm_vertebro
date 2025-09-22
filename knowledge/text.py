"""Helpers for extracting text from office documents."""

from __future__ import annotations

import io
import os
import re
import subprocess
import tempfile
from pathlib import Path

import structlog
from pypdf import PdfReader


logger = structlog.get_logger(__name__)

try:  # pragma: no cover - optional dependency in some environments
    import docx2txt  # type: ignore
except Exception:  # noqa: BLE001
    docx2txt = None


def extract_docx_text(data: bytes) -> str:
    """Return plain text extracted from a DOCX payload."""

    if docx2txt is None:
        logger.warning("docx_extract_unavailable", reason="docx2txt_not_installed")
        return ""

    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        tmp.write(data)
        tmp.flush()
        tmp_path = Path(tmp.name)

    try:
        text = docx2txt.process(tmp_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("docx_extract_failed", error=str(exc))
        text = ""
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:  # pragma: no cover - cleanup best effort
            pass

    return (text or "").strip()


def _run_textract(path: Path) -> str:
    try:
        import textract  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        return ""

    try:
        blob = textract.process(str(path))
    except Exception as exc:  # noqa: BLE001
        logger.debug("doc_extract_textract_failed", error=str(exc))
        return ""
    return blob.decode("utf-8", errors="ignore").strip()


def _run_antiword(path: Path) -> str:
    try:
        result = subprocess.run(
            ["antiword", str(path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:  # pragma: no cover - optional binary
        logger.debug("doc_extract_antiword_missing")
        return ""
    except subprocess.CalledProcessError as exc:  # noqa: BLE001
        logger.debug("doc_extract_antiword_failed", error=str(exc))
        return ""
    return result.stdout.decode("utf-8", errors="ignore").strip()


def extract_doc_text(data: bytes) -> str:
    """Return plain text extracted from a legacy DOC payload."""

    with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as tmp:
        tmp.write(data)
        tmp.flush()
        tmp_path = Path(tmp.name)

    try:
        text = _run_textract(tmp_path)
        if text:
            return text

        text = _run_antiword(tmp_path)
        if text:
            return text

        raw = tmp_path.read_bytes()
        decoded = raw.decode("utf-8", errors="ignore")
        cleaned = decoded.replace("\x00", " ")
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned.strip()
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:  # pragma: no cover - cleanup best effort
            pass


def extract_pdf_text(data: bytes) -> str:
    """Return plain text extracted from a PDF payload using :mod:`pypdf`."""

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # noqa: BLE001
        logger.debug("pdf_extract_open_failed", error=str(exc))
        return ""

    chunks: list[str] = []
    for index, page in enumerate(reader.pages):
        try:
            extracted = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            logger.debug("pdf_extract_page_failed", page=index, error=str(exc))
            continue
        if extracted:
            chunks.append(extracted.strip())

    return "\n\n".join(part for part in chunks if part).strip()
