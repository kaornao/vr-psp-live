#!/usr/bin/env python3
"""
Live local website:
  - serves the dashboard
  - background thread refreshes Bilibili status every N seconds
  - browser polls /api/live automatically

Keep this process running = auto-updating site.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

_lock = threading.Lock()
_state = {
    "status": None,
    "error": None,
    "refreshing": False,
    "last_ok_at": None,
}


def set_status(status: dict | None, error: str | None = None):
    with _lock:
        if status is not None:
            _state["status"] = status
            _state["last_ok_at"] = status.get("updated_at")
            _state["error"] = None
        if error is not None:
            _state["error"] = error
        _state["refreshing"] = False


def get_payload() -> dict:
    with _lock:
        return {
            "ok": _state["status"] is not None,
            "error": _state["error"],
            "refreshing": _state["refreshing"],
            "data": _state["status"],
        }


def refresh_once():
    from monitor import once, print_summary

    with _lock:
        _state["refreshing"] = True
    try:
        status = once()
        print_summary(status)
        set_status(status)
    except Exception as e:
        set_status(None, error=str(e))
        print(f"[refresh] {e}", flush=True)


def refresh_loop(interval: int, stop: threading.Event):
    # main() already did the first refresh; wait then continue
    while not stop.wait(interval):
        refresh_once()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        path = self.path.split("?", 1)[0]
        if path in ("/api/live", "/status.json") or path.endswith(".html"):
            super().log_message(fmt, *args)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html", "/live"):
            return self._send_file(ROOT / "live.html")
        if path == "/api/live":
            body = json.dumps(get_payload(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/status.json":
            payload = get_payload()
            data = payload.get("data") or {}
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def _send_file(self, path: Path):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    ap = argparse.ArgumentParser(description="VR/PSP live auto-updating website")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--interval", type=int, default=45, help="refresh seconds (min 30)")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    interval = max(30, args.interval)

    # Warm first snapshot before opening browser when possible
    print("Refreshing live status...", flush=True)
    refresh_once()

    stop = threading.Event()
    t = threading.Thread(target=refresh_loop, args=(interval, stop), daemon=True)
    t.start()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print("=" * 50, flush=True)
    print(f"Live board: {url}", flush=True)
    print(f"Auto refresh every {interval}s. Keep this window OPEN.", flush=True)
    print("Press Ctrl+C to stop.", flush=True)
    print("=" * 50, flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        stop.set()
        print("\nStopped.", flush=True)


if __name__ == "__main__":
    main()
