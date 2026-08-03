from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard_v2.dashboard_state import build_dashboard_state
from dashboard_v2.render import render_html


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "AIStockBotDashboardV2/1.0"

    def log_message(self, format, *args):
        return

    def send_payload(self, body: bytes, content_type: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        state = build_dashboard_state(ROOT)
        if path in {"/", "/index.html"}:
            self.send_payload(
                render_html(state).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        if path == "/api/state":
            self.send_payload(
                (json.dumps(state, indent=2, sort_keys=True) + "\n").encode(
                    "utf-8"
                ),
                "application/json; charset=utf-8",
            )
            return
        if path == "/health":
            self.send_payload(b'{"status":"ok"}\n', "application/json")
            return
        self.send_payload(b"Not Found\n", "text/plain; charset=utf-8", 404)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()

    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Dashboard v2 only permits localhost binding.")

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"DASHBOARD_URL=http://{args.host}:{args.port}")
    print("Read-only local server. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
