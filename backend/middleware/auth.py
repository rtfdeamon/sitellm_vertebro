"""Authentication middleware."""

import base64
import hashlib
import hmac
from uuid import uuid4

import structlog
from fastapi import Request, Response
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.auth import ADMIN_PASSWORD_DIGEST, ADMIN_USER
from backend.middleware.admin import AdminIdentity
from mongo import MongoClient

logger = structlog.get_logger(__name__)


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for Basic Auth and session management."""

    _PROTECTED_PREFIXES = (
        "/admin",
        "/api/v1/admin",
        "/api/v1/backup",
        "/api/v1/crawler",
        "/api/intelligent-processing",
    )
    # Exact method+path pairs that must be admin-protected even if their prefix is different
    # Keep minimal and explicit to avoid over-protecting public APIs like crawler status.
    _PROTECTED_EXACT: set[tuple[str, str]] = {
        ("POST", "/api/v1/crawler/reset"),
        ("POST", "/api/v1/crawler/deduplicate"),
        ("POST", "/api/v1/crawler/stop"),
    }

    # Session storage: username -> AdminIdentity
    _sessions: dict[str, AdminIdentity] = {}

    @staticmethod
    def _unauthorized_response(request: Request) -> Response:
        path = request.url.path
        accept = request.headers.get("Accept", "")
        wants_json = path.startswith("/api/") or "application/json" in accept
        if wants_json:
            return ORJSONResponse({"detail": "Unauthorized"}, status_code=401)
        return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="admin"'})

    async def _authenticate(self, request: Request, username: str, password: str) -> AdminIdentity | None:
        normalized_username = username.strip().lower()
        print(f"DEBUG: Auth attempt: {normalized_username} vs {ADMIN_USER.strip().lower()}")
        if normalized_username == ADMIN_USER.strip().lower():
            logger.debug("basic_auth_attempt_super", username=normalized_username)
            hashed = hashlib.sha256(password.encode()).digest()
            print(f"DEBUG: Hash comparison: {hashed.hex()} vs {ADMIN_PASSWORD_DIGEST.hex()}")
            if hmac.compare_digest(hashed, ADMIN_PASSWORD_DIGEST):
                logger.debug("admin_super_login_success", username=normalized_username)
                return AdminIdentity(username=normalized_username, is_super=True)
            else:
                logger.warning("admin_super_login_failed", username=normalized_username)
                return None

        mongo_client: MongoClient | None = getattr(request.app.state, "mongo", None)
        if not mongo_client:
            return None

        try:
            project = await mongo_client.get_project_by_admin_username(normalized_username)
        except Exception as exc:  # noqa: BLE001
            logger.warning("project_admin_lookup_failed", username=normalized_username, error=str(exc))
            return None

        if not project or not project.admin_password_hash:
            return None

        candidate_hash = hashlib.sha256(password.encode()).hexdigest()
        stored_hash = project.admin_password_hash.strip().lower()
        if not hmac.compare_digest(candidate_hash, stored_hash):
            return None

        return AdminIdentity(
            username=normalized_username,
            is_super=False,
            projects=(project.name,),
        )

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method.upper()
        normalized_path = path.rstrip("/") or "/"
        is_protected = (
            any(path.startswith(prefix) for prefix in self._PROTECTED_PREFIXES)
            or (method, normalized_path) in self._PROTECTED_EXACT
        )
        if not is_protected:
            return await call_next(request)

        # Check for existing session cookie first
        session_token = request.cookies.get("admin_session")
        if session_token and session_token in self._sessions:
            identity = self._sessions[session_token]
            request.state.admin = identity
            return await call_next(request)

        # Try HTTP Basic Auth
        auth = request.headers.get("Authorization")
        if auth and auth.lower().startswith("basic "):
            encoded = ""
            try:
                encoded = auth.split(" ", 1)[1].strip()
                raw_bytes = base64.b64decode(encoded.encode("ascii", "ignore"))
                decoded = raw_bytes.decode("utf-8", errors="ignore").strip()
                if ":" not in decoded:
                    logger.warning("admin_auth_malformed_header")
                    return self._unauthorized_response(request)
                username, password = decoded.split(":", 1)
                identity = await self._authenticate(request, username, password)
                if identity:
                    request.state.admin = identity
                    # Create session token and store it
                    session_token = hashlib.sha256(f"{username}:{uuid4()}".encode()).hexdigest()
                    self._sessions[session_token] = identity
                    response = await call_next(request)
                    # Set cookie with session token
                    response.set_cookie(
                        key="admin_session",
                        value=session_token,
                        httponly=True,
                        samesite="lax",
                        max_age=86400  # 24 hours
                    )
                    return response
                logger.warning("admin_auth_invalid_credentials", username=username)
            except Exception as exc:  # noqa: BLE001
                print(f"DEBUG: BasicAuthMiddleware caught exception: {exc}")
                logger.warning(
                    "basic_auth_decode_failed",
                    error=str(exc),
                    auth_header=request.headers.get("Authorization"),
                )
                return self._unauthorized_response(request)

        return self._unauthorized_response(request)
