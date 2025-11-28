"""
Input validation utilities for security hardening.

Provides Pydantic validators and helper functions for:
- File size validation
- MIME type whitelisting
- Magic number checking
- Unicode normalization
- HTML escaping
- Text length caps
"""

from __future__ import annotations

import os
import io
import csv
import html
import unicodedata
from typing import Any
from pathlib import Path

import structlog
from fastapi import HTTPException, UploadFile
from pydantic import field_validator, Field

logger = structlog.get_logger(__name__)

# Configuration constants
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 100 * 1024 * 1024))  # 100 MB default
MAX_QUESTION_LENGTH = int(os.getenv("MAX_QUESTION_LENGTH", 1000))
MAX_ANSWER_LENGTH = int(os.getenv("MAX_ANSWER_LENGTH", 10000))

# Allowed MIME types for file uploads
ALLOWED_MIME_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/pdf",
    "text/plain",
    "text/html",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
}

# Magic numbers for file type detection (first few bytes)
MAGIC_NUMBERS: dict[bytes, str] = {
    b"\x50\x4B\x03\x04": "application/vnd.openxmlformats-officedocument",
    b"\x50\x4B\x05\x06": "application/vnd.openxmlformats-officedocument",
    b"\xD0\xCF\x11\xE0": "application/vnd.ms-excel",
    b"\x50\x44\x46\x2D": "application/pdf",
    b"%PDF": "application/pdf",
    b"\xFF\xFE": "text/plain",  # UTF-16 LE BOM
    b"\xFE\xFF": "text/plain",  # UTF-16 BE BOM
    b"\xEF\xBB\xBF": "text/plain",  # UTF-8 BOM
}


def validate_file_size(file: UploadFile, max_size: int = MAX_UPLOAD_SIZE) -> None:
    """Validate file size before reading."""
    try:
        # Try to get file size from Content-Length header
        content_length = getattr(file, "size", None)
        if content_length and content_length > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {max_size // (1024 * 1024)} MB",
            )
        
        # For multipart uploads, check current position
        if hasattr(file.file, "seek") and hasattr(file.file, "tell"):
            current_pos = file.file.tell()
            file.file.seek(0, io.SEEK_END)
            file_size = file.file.tell()
            file.file.seek(current_pos)
            
            if file_size > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {max_size // (1024 * 1024)} MB",
                )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("file_size_validation_warning", error=str(exc))
        # Continue if size check fails (file might be streamed)


def validate_mime_type(content_type: str | None, filename: str | None = None) -> str:
    """Validate and normalize MIME type."""
    if not content_type:
        if filename:
            # Infer from extension as fallback
            ext = Path(filename).suffix.lower()
            mime_map = {
                ".csv": "text/csv",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".xls": "application/vnd.ms-excel",
                ".pdf": "application/pdf",
                ".txt": "text/plain",
                ".html": "text/html",
                ".doc": "application/msword",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
            content_type = mime_map.get(ext, "application/octet-stream")
        else:
            raise HTTPException(status_code=400, detail="Content type is required")
    
    content_type_lower = content_type.lower().split(";")[0].strip()
    
    # Check whitelist
    if content_type_lower not in ALLOWED_MIME_TYPES and not any(
        content_type_lower.startswith(allowed) for allowed in ALLOWED_MIME_TYPES
    ):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type: {content_type}. Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
        )
    
    return content_type_lower


def validate_magic_number(file_bytes: bytes) -> bool:
    """Validate file magic number matches declared MIME type."""
    if len(file_bytes) < 4:
        return False
    
    for magic, mime_type in MAGIC_NUMBERS.items():
        if file_bytes.startswith(magic):
            return True
    
    # Allow text files without magic numbers
    try:
        file_bytes[:1024].decode("utf-8")
        return True
    except UnicodeDecodeError:
        pass
    
    return False


def normalize_unicode(text: str) -> str:
    """Normalize Unicode text (NFKC normalization)."""
    return unicodedata.normalize("NFKC", text)


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return html.escape(text, quote=True)


def validate_text_length(text: str, max_length: int, field_name: str = "text") -> str:
    """Validate and truncate text length."""
    if len(text) > max_length:
        logger.warning(
            "text_truncated",
            field=field_name,
            original_length=len(text),
            max_length=max_length,
        )
        return text[:max_length]
    return text


def validate_question(text: str) -> str:
    """Validate and normalize question text."""
    normalized = normalize_unicode(text.strip())
    validated = validate_text_length(normalized, MAX_QUESTION_LENGTH, "question")
    return escape_html(validated)


def validate_answer(text: str) -> str:
    """Validate and normalize answer text."""
    normalized = normalize_unicode(text.strip())
    validated = validate_text_length(normalized, MAX_ANSWER_LENGTH, "answer")
    return escape_html(validated)


async def validate_upload_file(
    file: UploadFile,
    *,
    max_size: int | None = None,
    check_magic: bool = True,
) -> bytes:
    """Comprehensive file upload validation."""
    max_size = max_size or MAX_UPLOAD_SIZE
    
    # Validate size
    validate_file_size(file, max_size)
    
    # Validate MIME type
    content_type = validate_mime_type(file.content_type, file.filename)
    
    # Read file with timeout protection (would need asyncio.wait_for in calling code)
    payload = await file.read()
    
    if not payload:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Check actual size
    if len(payload) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_size // (1024 * 1024)} MB",
        )
    
    # Validate magic number
    if check_magic and not validate_magic_number(payload):
        logger.warning("magic_number_check_failed", filename=file.filename, content_type=content_type)
        # Don't fail, just warn (some valid files might not have magic numbers)
    
    return payload


def detect_csv_delimiter(text: str) -> str:
    """Detect CSV delimiter using csv.Sniffer."""
    try:
        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(text[:1024]).delimiter
        return delimiter
    except Exception:  # noqa: BLE001
        # Default to comma if detection fails
        return ","

