"""Desktop widget API endpoints."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.auth import require_admin
from backend.desktop import prepare_desktop_artifact_blocking

router = APIRouter(prefix="/desktop", tags=["desktop"])


class DesktopBuildRequest(BaseModel):
    platform: Literal["windows", "linux-appimage", "linux-deb"]


@router.post("/build")
async def desktop_build(
    request: Request,
    payload: DesktopBuildRequest,
    _: Any = Depends(require_admin),
):
    """
    Trigger build of desktop widget artifact.

    This is a blocking operation that runs 'npm run build:...' on the server.
    Returns the built artifact file for download.
    """
    try:
        artifact = prepare_desktop_artifact_blocking(payload.platform)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    filename = artifact.name
    return FileResponse(
        path=artifact,
        filename=filename,
        media_type="application/octet-stream",
    )
