#!/usr/bin/env python3
"""
Простая «ожидалка» зависимостей, чтобы приложение не падало в early-boot.
Использование (из entrypoint перед стартом сервера):
  python -m scripts.wait_for --tcp redis:6379 --tcp mongo:27017 --http http://qdrant:6333/readyz
"""
import argparse, socket, sys, time, urllib.request

def wait_tcp(host: str, port: int, timeout=2.0) -> bool:
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()

def wait_http(url: str, timeout=2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            ok = 200 <= r.status < 400
            if not ok:
                print(f"unexpected status {r.status} for {url}", file=sys.stderr)
            return ok
    except Exception:
        return False

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tcp", action="append", default=[], help="host:port")
    p.add_argument("--http", action="append", default=[], help="http(s)://...")
    p.add_argument("--retries", type=int, default=60)
    p.add_argument("--sleep", type=float, default=1.5)
    a = p.parse_args()

    for _ in range(a.retries):
        ok = True
        for hp in a.tcp:
            host, port = hp.split(":")
            ok &= wait_tcp(host, int(port))
        for u in a.http:
            ok &= wait_http(u)
        if ok:
            return 0
        time.sleep(a.sleep)
    return 1

if __name__ == "__main__":
    sys.exit(main())
