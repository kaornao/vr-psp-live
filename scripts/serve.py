#!/usr/bin/env python3
"""本机预览：托管仓库根目录静态页，并可选自动刷新 status.json。"""
from __future__ import annotations

import argparse
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        if self.path.startswith("/status.json") or self.path.endswith(".html"):
            super().log_message(fmt, *args)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/",):
            self.path = "/index.html"
        return super().do_GET()


def refresh_loop(interval: int, stop: threading.Event):
    from monitor import once, print_summary

    while not stop.is_set():
        try:
            print_summary(once())
        except Exception as e:
            print(f"[refresh] {e}", flush=True)
        stop.wait(interval)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--no-refresh", action="store_true")
    args = ap.parse_args()

    try:
        from monitor import once, print_summary

        print_summary(once())
    except Exception as e:
        print(f"[warn] 首次刷新失败: {e}", flush=True)

    stop = threading.Event()
    if not args.no_refresh:
        t = threading.Thread(
            target=refresh_loop, args=(max(30, args.interval), stop), daemon=True
        )
        t.start()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"看板: {url}", flush=True)
    print("Ctrl+C 退出", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        stop.set()
        print("\n已停止", flush=True)


if __name__ == "__main__":
    main()
