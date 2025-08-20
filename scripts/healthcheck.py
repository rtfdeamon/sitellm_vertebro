import os
import sys
import urllib.request

# Адрес эндпоинта здоровья
url = os.environ.get("HEALTHCHECK_URL")
if not url:
    port = os.environ.get("PORT", "8000")
    url = f"http://127.0.0.1:{port}/healthz"

def main() -> int:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            if resp.status == 200:
                return 0
            return 1
    except Exception:
        return 1

if __name__ == "__main__":
    sys.exit(main())
