"""Tiny HTTP health check helper for container use.

The script probes ``HEALTHCHECK_URL`` (or ``http://127.0.0.1:${PORT}/healthz``)
and returns a proper exit code for Docker healthchecks.
"""

import os
import sys
import urllib.request

# Адрес эндпоинта здоровья
url = os.environ.get("HEALTHCHECK_URL")
if not url:
    port = os.environ.get("PORT", "8000")
    url = f"http://127.0.0.1:{port}/healthz"

def main() -> int:
    """Return ``0`` if the endpoint responds with HTTP 200, else ``1``."""
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            if resp.status == 200:
                return 0
            return 1
    except Exception:
        return 1

if __name__ == "__main__":
    sys.exit(main())
