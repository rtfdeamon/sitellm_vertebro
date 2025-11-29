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
    if len(lines) > 5:
        remaining = len(lines) - 5
        lines = lines[:5]
        lines.append(f"... и ещё {remaining} файлов")
    return lines


def project_telegram_payload(
    project: Any,  # Typed as Any to avoid circular imports with models/hubs
    controller: Any = None,
) -> dict[str, Any]:
    """Build Telegram bot status payload."""
    running = False
    error = None
    if controller and controller.is_project_running(project.name):
        running = True
    if controller:
        error = controller.get_last_error(project.name)

    return {
        "enabled": bool(project.telegram_token),
        "token_set": bool(project.telegram_token),
        "token_preview": f"{project.telegram_token[:4]}…{project.telegram_token[-2:]}" if project.telegram_token and len(project.telegram_token) > 6 else None,
        "auto_start": bool(project.telegram_auto_start),
        "running": running,
        "error": error,
        "username": None,  # Could be fetched if we stored it
    }


def project_max_payload(
    project: Any,
    controller: Any = None,
) -> dict[str, Any]:
    """Build MAX bot status payload."""
    running = False
    error = None
    if controller and controller.is_project_running(project.name):
        running = True
    if controller:
        error = controller.get_last_error(project.name)

    return {
        "enabled": bool(project.max_token),
        "token_set": bool(project.max_token),
        "token_preview": f"{project.max_token[:4]}…{project.max_token[-2:]}" if project.max_token and len(project.max_token) > 6 else None,
        "auto_start": bool(project.max_auto_start),
        "running": running,
        "error": error,
    }


def project_vk_payload(
    project: Any,
    controller: Any = None,
) -> dict[str, Any]:
    """Build VK bot status payload."""
    running = False
    error = None
    if controller and controller.is_project_running(project.name):
        running = True
    if controller:
        error = controller.get_last_error(project.name)

    return {
        "enabled": bool(project.vk_token),
        "token_set": bool(project.vk_token),
        "token_preview": f"{project.vk_token[:4]}…{project.vk_token[-2:]}" if project.vk_token and len(project.vk_token) > 6 else None,
        "auto_start": bool(project.vk_auto_start),
        "running": running,
        "error": error,
    }
