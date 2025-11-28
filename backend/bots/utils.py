"""Bot utility functions."""

from typing import Any


def format_attachment_preview_lines(attachments: list[dict[str, Any]]) -> list[str]:
    """Format attachment preview lines for confirmation messages."""
    lines: list[str] = []
    for idx, attachment in enumerate(attachments, 1):
        name = str(
            attachment.get("name")
            or attachment.get("title")
            or attachment.get("filename")
            or f"Документ {idx}"
        )
        description = attachment.get("description")
        if isinstance(description, str):
            description = description.strip()
        else:
            description = ""
        if description and len(description) > 120:
            description = description[:117].rstrip() + "…"
        download = (
            attachment.get("download_url")
            or attachment.get("url")
            or attachment.get("link")
        )
        parts = [f"{idx}. {name}"]
        if description:
            parts.append(description)
        if download:
            parts.append(str(download))
        lines.append(" — ".join(parts))
    return lines
