from __future__ import annotations
import json
from http import HTTPStatus
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import urlparse

from .api import TradingConfigurationService


STATIC_ROOT = (
    Path(__file__).resolve().parent / "static"
)


class ConfigurationHandler(
    BaseHTTPRequestHandler
):
    service: TradingConfigurationService | None = None

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
        size = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
        )
        if size <= 0:
            return {}
        value = json.loads(
            self.rfile.read(size).decode(
                "utf-8"
            )
        )
        return value if isinstance(
            value,
            dict,
        ) else {}

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
                            "trading_configuration"
                        ),
                        "mode": "DRAFT_ONLY",
                        "activation_enabled": False,
                        "broker_write_enabled": False,
                        "order_submission_enabled": False,
                    },
                )
                return
            if path == "/api/schema":
                self._json(
                    HTTPStatus.OK,
                    self.service.schema(),
                )
                return
            if path == "/api/current":
                self._json(
                    HTTPStatus.OK,
                    self.service.current(),
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
            body = self._body()
            if path == "/api/validate":
                self._json(
                    HTTPStatus.OK,
                    self.service.validate(body),
                )
                return
            if path == "/api/save-draft":
                self._json(
                    HTTPStatus.CREATED,
                    self.service.save(body),
                )
                return
            if path == "/api/activate":
                self.service.activate(body)
            self._json(
                HTTPStatus.NOT_FOUND,
                {"error": "NOT_FOUND"},
            )
        except PermissionError as exc:
            self._json(
                HTTPStatus.FORBIDDEN,
                {"error": str(exc)},
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
    draft_path: Path,
    ledger_path: Path,
    host: str = "127.0.0.1",
    port: int = 8770,
) -> None:
    ConfigurationHandler.service = (
        TradingConfigurationService(
            draft_path=draft_path,
            ledger_path=ledger_path,
        )
    )
    server = ThreadingHTTPServer(
        (host, port),
        ConfigurationHandler,
    )
    print(
        "Profile Strategy Risk Configuration: "
        f"http://{host}:{port}"
    )
    print("Configuration Mode: DRAFT ONLY")
    print("Activation: OFF")
    print("Broker Write: OFF")
    print("Order Submission: OFF")
    server.serve_forever()
