from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dashboard.advanced_monitoring import build_advanced_payload
from dashboard.data_loader import load_dashboard_sources
from dashboard.panels import build_dashboard_payload


class DashboardHandler(BaseHTTPRequestHandler):
    repository_root: Path
    static_root: Path

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/dashboard":
            self._send_json(
                build_dashboard_payload(
                    load_dashboard_sources(self.repository_root)
                )
            )
            return
        if route == "/api/advanced":
            self._send_json(
                build_advanced_payload(self.repository_root)
            )
            return

        relative = "index.html" if route in {"", "/"} else route.lstrip("/")
        target = (self.static_root / relative).resolve()
        root = self.static_root.resolve()
        if root not in target.parents and target != root:
            self.send_error(403)
            return
        if not target.exists() or not target.is_file():
            self.send_error(404)
            return

        content = target.read_bytes()
        content_type, _ = mimetypes.guess_type(str(target))
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, payload: dict) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def run_server(repository_root: Path, host: str, port: int) -> None:
    handler = DashboardHandler
    handler.repository_root = repository_root.resolve()
    handler.static_root = (repository_root / "dashboard/static").resolve()
    server = ThreadingHTTPServer((host, port), handler)
    print(f"DASHBOARD_URL=http://{host}:{port}")
    print("READ_ONLY=true")
    print("ADVANCED_MONITORING=true")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    args = parser.parse_args()
    if args.port < 1024 or args.port > 65535:
        raise SystemExit("Port must be between 1024 and 65535.")
    run_server(Path(args.repository_root), args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
