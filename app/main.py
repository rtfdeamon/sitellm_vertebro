"""FastAPI application factory.

Provides create_app() function to create and configure FastAPI application instance.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from observability.metrics import MetricsMiddleware, metrics_app
from backend.rate_limiting import RateLimitingMiddleware
from backend.csrf import CSRFMiddleware
from backend.csp import CSPMiddleware
from backend.gzip_middleware import GZipMiddleware

from api import (
    llm_router,
    crawler_router,
    reading_router,
    voice_router,
)
from voice import voice_assistant_router


def create_app(*, debug: bool | None = None) -> FastAPI:
    """Create and configure FastAPI application instance.
    
    Parameters
    ----------
    debug
        Enable debug mode. If None, uses settings.debug.
    
    Returns
    -------
    FastAPI
        Configured FastAPI application instance.
    """
    # Import here to avoid circular dependency
    from app import lifespan, BasicAuthMiddleware, _ssl_enabled, _parse_cors_origins
    from settings import Settings
    
    settings = Settings()
    use_debug = debug if debug is not None else settings.debug
    
    # Create FastAPI app with lifespan
    app = FastAPI(lifespan=lifespan, debug=use_debug)
    
    # Add ProxyHeadersMiddleware if SSL is enabled
    if _ssl_enabled():
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
    
    # Configure CORS
    cors_origins = _parse_cors_origins(getattr(settings, "cors_origins", "*"))
    allow_all_origins = "*" in cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all_origins else cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add other middleware in order (first added = last executed)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(CSPMiddleware)  # CSP headers first
    app.add_middleware(GZipMiddleware)  # GZip compression
    app.add_middleware(RateLimitingMiddleware)  # Rate limiting before auth
    app.add_middleware(CSRFMiddleware)  # CSRF protection for state-changing requests
    app.add_middleware(BasicAuthMiddleware)  # Basic auth last (executes first)
    
    # Mount metrics app
    app.mount("/metrics", metrics_app)
    
    # Include API routers from api.py
    app.include_router(llm_router, prefix="/api/v1")
    app.include_router(crawler_router, prefix="/api/v1")
    app.include_router(reading_router, prefix="/api/v1")
    app.include_router(voice_router, prefix="/api/v1")
    app.include_router(voice_assistant_router, prefix="/api/v1")
    
    # Include admin routers
    from app.routers import (
        backup as backup_router,
        stats as stats_router,
        admin as admin_router,
        projects as projects_router,
        knowledge as knowledge_router,
        llm as llm_admin_router,
    )
    
    app.include_router(backup_router.router)
    app.include_router(stats_router.router)
    app.include_router(admin_router.router)
    app.include_router(projects_router.router)
    app.include_router(knowledge_router.router)
    app.include_router(llm_admin_router.router)
    
    # Mount static files
    app.mount("/widget", StaticFiles(directory="widget", html=True), name="widget")
    app.mount("/admin", StaticFiles(directory="admin", html=True), name="admin")
    
    return app

