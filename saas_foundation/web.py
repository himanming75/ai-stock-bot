from __future__ import annotations
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .control_plane import SaaSControlPlane


DASHBOARD_PATH = (
    Path(__file__).resolve().parent
    / "static"
    / "index.html"
)


class SaaSRequestHandler(BaseHTTPRequestHandler):
    control_plane: SaaSControlPlane | None = None

    def _json(self, status: int, payload: dict | list) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(
            self.rfile.read(length).decode("utf-8")
        )

    def _user(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise PermissionError("AUTH_REQUIRED")
        return self.control_plane.authenticate(
            header.removeprefix("Bearer ").strip()
        )

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/health":
                self._json(HTTPStatus.OK, {
                    "status": "HEALTHY",
                    "service": "saas_foundation",
                    "broker_write_enabled": False,
                    "order_submission_enabled": False,
                })
                return
            if path == "/":
                raw = DASHBOARD_PATH.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8",
                )
                self.send_header(
                    "Content-Length",
                    str(len(raw)),
                )
                self.end_headers()
                self.wfile.write(raw)
                return
            self._json(
                HTTPStatus.NOT_FOUND,
                {"error": "NOT_FOUND"},
            )
        except Exception as exc:
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"error": str(exc)},
            )

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/register":
                result = self.control_plane.register(
                    email=body["email"],
                    password=body["password"],
                    workspace_name=body["workspace_name"],
                )
                self._json(HTTPStatus.CREATED, result)
                return
            if path == "/api/login":
                token = self.control_plane.login(
                    email=body["email"],
                    password=body["password"],
                )
                self._json(HTTPStatus.OK, {
                    "access_token": token,
                    "token_type": "Bearer",
                })
                return
            if path == "/api/workspace/summary":
                user = self._user()
                result = self.control_plane.workspace_summary(
                    user_id=user.user_id,
                    workspace_id=body["workspace_id"],
                )
                self._json(HTTPStatus.OK, result)
                return
            self._json(
                HTTPStatus.NOT_FOUND,
                {"error": "NOT_FOUND"},
            )
        except PermissionError as exc:
            self._json(
                HTTPStatus.UNAUTHORIZED,
                {"error": str(exc)},
            )
        except Exception as exc:
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"error": str(exc)},
            )


def serve(
    control_plane: SaaSControlPlane,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    SaaSRequestHandler.control_plane = control_plane
    server = ThreadingHTTPServer(
        (host, port),
        SaaSRequestHandler,
    )
    print(f"SaaS Foundation: http://{host}:{port}")
    server.serve_forever()
