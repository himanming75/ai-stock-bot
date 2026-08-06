from __future__ import annotations
import json
from http import HTTPStatus
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import urlparse

from .api import CommandCenterService
from .config import CommandCenterPaths


STATIC_ROOT = (
    Path(__file__).resolve().parent / "static"
)


class CommandCenterHandler(
    BaseHTTPRequestHandler
):
    service: CommandCenterService | None = None

    def _json(self, status: int, payload) -> None:
        raw = json.dumps(
            payload,
            default=str,
        ).encode("utf-8")
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

    def _static(
        self,
        filename: str,
        content_type: str,
    ) -> None:
        raw = (
            STATIC_ROOT / filename
        ).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            content_type,
        )
        self.send_header(
            "Content-Length",
            str(len(raw)),
        )
        self.end_headers()
        self.wfile.write(raw)

    def _body(self) -> dict:
        length = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
        )
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        value = json.loads(
            raw.decode("utf-8")
        )
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/":
                self._static(
                    "index.html",
                    "text/html; charset=utf-8",
                )
                return
            if path == "/styles.css":
                self._static(
                    "styles.css",
                    "text/css; charset=utf-8",
                )
                return
            if path == "/app.js":
                self._static(
                    "app.js",
                    "application/javascript; charset=utf-8",
                )
                return
            if path == "/health":
                self._json(
                    HTTPStatus.OK,
                    {
                        "status": "HEALTHY",
                        "service": (
                            "paper_command_center"
                        ),
                        "mode": (
                            "DRY_RUN_COMMAND_PLANNING"
                        ),
                        "broker_write_enabled": False,
                        "order_submission_enabled": False,
                        "process_execution_enabled": False,
                    },
                )
                return
            if path == "/api/status":
                self._json(
                    HTTPStatus.OK,
                    self.service.status(),
                )
                return
            self._json(
                HTTPStatus.NOT_FOUND,
                {"error": "NOT_FOUND"},
            )
        except Exception as exc:
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": str(exc)},
            )

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path != "/api/command-plan":
                self._json(
                    HTTPStatus.NOT_FOUND,
                    {"error": "NOT_FOUND"},
                )
                return
            body = self._body()
            plan = self.service.command_plan(
                action=str(
                    body.get("action") or ""
                ),
                requested_by=str(
                    body.get("requested_by")
                    or "LOCAL_USER"
                ),
                reason=str(
                    body.get("reason") or ""
                ),
            )
            self._json(
                HTTPStatus.CREATED,
                plan,
            )
        except ValueError as exc:
            self._json(
                HTTPStatus.BAD_REQUEST,
                {"error": str(exc)},
            )
        except Exception as exc:
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": str(exc)},
            )


def serve(
    *,
    paths: CommandCenterPaths,
    host: str = "127.0.0.1",
    port: int = 8769,
) -> None:
    CommandCenterHandler.service = (
        CommandCenterService(paths=paths)
    )
    server = ThreadingHTTPServer(
        (host, port),
        CommandCenterHandler,
    )
    print(
        "Paper Runtime Command Center: "
        f"http://{host}:{port}"
    )
    print("Command Execution: OFF")
    print("Process Start/Stop: OFF")
    print("Broker Write: OFF")
    print("Order Submission: OFF")
    server.serve_forever()
