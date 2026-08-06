from __future__ import annotations
import json
from http import HTTPStatus
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import urlparse

from .control_plane import SaaSSecurityControlPlane


STATIC_ROOT = Path(__file__).resolve().parent / "static"


class SecurityRequestHandler(BaseHTTPRequestHandler):
    control: SaaSSecurityControlPlane | None = None

    def _json(
        self,
        status: int,
        payload: dict | list,
    ) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header(
            "Content-Length",
            str(len(raw)),
        )
        self.end_headers()
        self.wfile.write(raw)

    def _serve(self, filename: str) -> None:
        path = STATIC_ROOT / filename
        raw = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            (
                "text/html; charset=utf-8"
                if filename.endswith(".html")
                else "text/css; charset=utf-8"
            ),
        )
        self.send_header(
            "Content-Length",
            str(len(raw)),
        )
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._serve("index.html")
            return
        if path == "/styles.css":
            self._serve("styles.css")
            return
        if path == "/health":
            self._json(
                HTTPStatus.OK,
                {
                    "status": "HEALTHY",
                    "service": "saas_security",
                    "broker_write_enabled": False,
                    "order_submission_enabled": False,
                },
            )
            return
        self._json(
            HTTPStatus.NOT_FOUND,
            {"error": "NOT_FOUND"},
        )


def serve(
    control: SaaSSecurityControlPlane,
    *,
    host: str = "127.0.0.1",
    port: int = 8766,
) -> None:
    SecurityRequestHandler.control = control
    server = ThreadingHTTPServer(
        (host, port),
        SecurityRequestHandler,
    )
    print(
        f"SaaS Security Console: http://{host}:{port}"
    )
    server.serve_forever()
