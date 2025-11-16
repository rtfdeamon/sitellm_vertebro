"""LLM and Ollama management router.

Provides endpoints for LLM model management and Ollama cluster configuration.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import ORJSONResponse

from app.services.auth import require_admin, require_super_admin
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/admin", tags=["llm"])


@router.get("/llm/models", response_class=ORJSONResponse)
def admin_llm_models() -> ORJSONResponse:
    """Return available LLM model identifiers."""
    # Import here to avoid circular dependency
    from backend.settings import settings as base_settings
    
    models = base_settings.get_available_llm_models()
    return ORJSONResponse({"models": models})


@router.get("/llm/availability", response_class=ORJSONResponse)
async def admin_llm_availability(request: Request) -> ORJSONResponse:
    """Expose a simple availability flag for the LLM cluster."""
    # Import here to avoid circular dependency
    from app import admin_llm_availability as _availability_impl
    return await _availability_impl(request)


@router.get("/ollama/catalog", response_class=ORJSONResponse)
async def admin_ollama_catalog(request: Request) -> ORJSONResponse:
    """Return Ollama model catalog."""
    # Import here to avoid circular dependency
    # The full implementation is still in app.py (complex function with many dependencies)
    # TODO: Move full implementation to this router in future iteration
    from app import admin_ollama_catalog as _catalog_impl
    return await _catalog_impl(request)


class OllamaServerPayload(BaseModel):
    base_url: str
    label: str | None = None
    enabled: bool = True


@router.get("/ollama/servers", response_class=ORJSONResponse)
async def admin_ollama_servers(request: Request) -> ORJSONResponse:
    """List configured Ollama servers."""
    # Import here to avoid circular dependency
    # The implementation is still in app.py
    from app import admin_ollama_servers as _servers_impl
    return await _servers_impl(request)


@router.post("/ollama/servers", response_class=ORJSONResponse)
async def admin_create_ollama_server(
    request: Request,
    payload: OllamaServerPayload,
) -> ORJSONResponse:
    """Create or update an Ollama server configuration."""
    # Import here to avoid circular dependency
    # The implementation is still in app.py
    from app import admin_ollama_server_upsert as _upsert_impl
    return await _upsert_impl(request, payload)


@router.delete("/ollama/servers/{name}", response_class=ORJSONResponse)
async def admin_ollama_server_delete(request: Request, name: str) -> ORJSONResponse:
    """Delete an Ollama server configuration."""
    # Import here to avoid circular dependency
    # The implementation is still in app.py
    from app import admin_ollama_server_delete as _delete_impl
    return await _delete_impl(request, name)


class OllamaInstallPayload(BaseModel):
    model: str


@router.post("/ollama/install", response_class=ORJSONResponse)
async def admin_ollama_install(
    request: Request,
    payload: OllamaInstallPayload,
) -> ORJSONResponse:
    """Schedule Ollama model installation."""
    # Import here to avoid circular dependency
    # The implementation is still in app.py
    from app import admin_ollama_install as _install_impl
    # Convert payload to match app.py signature
    class OllamaInstallRequest:
        def __init__(self, model: str):
            self.model = model
    install_req = OllamaInstallRequest(payload.model)
    return await _install_impl(request, install_req)

