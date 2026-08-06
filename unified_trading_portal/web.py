from __future__ import annotations
import json
from http import HTTPStatus
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import urlparse

from .api import UnifiedPortalDataService


STATIC_ROOT = (
    Path(__file__).resolve().parent / "static"
)


class UnifiedPortalHandler(BaseHTTPRequestHandler):
    service: UnifiedPortalDataService | None = None

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
                            "unified_trading_portal"
                        ),
                        "mode": "READ_ONLY",
                        "broker_write_enabled": False,
                        "order_submission_enabled": False,
                        "order_cancel_enabled": False,
                    },
                )
                return
            if path == "/api/dashboard":
                self._json(
                    HTTPStatus.OK,
                    self.service.dashboard(),
                )
                return
            if path == "/api/accounts":
                self._json(
                    HTTPStatus.OK,
                    self.service.accounts(),
                )
                return
            if path == "/api/positions":
                self._json(
                    HTTPStatus.OK,
                    self.service.positions(),
                )
                return
            if path == "/api/orders":
                self._json(
                    HTTPStatus.OK,
                    self.service.orders(),
                )
                return
            if path == "/api/reconciliation":
                self._json(
                    HTTPStatus.OK,
                    self.service.reconciliation(),
                )
                return
            self._json(
                HTTPStatus.NOT_FOUND,
                {"error": "NOT_FOUND"},
            )
        except Exception as exc:
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "error": str(exc),
                    "broker_write_enabled": False,
                    "order_submission_enabled": False,
                },
            )

    def log_message(
        self,
        format: str,
        *args,
    ) -> None:
        print(
            "%s - - [%s] %s"
            % (
                self.address_string(),
                self.log_date_time_string(),
                format % args,
            )
        )


def serve(
    *,
    portal_path: Path,
    sync_result_path: Path,
    host: str = "127.0.0.1",
    port: int = 8768,
) -> None:
    UnifiedPortalHandler.service = (
        UnifiedPortalDataService(
            portal_path=portal_path,
            sync_result_path=sync_result_path,
        )
    )
    server = ThreadingHTTPServer(
        (host, port),
        UnifiedPortalHandler,
    )
    print(
        "Unified Trading Portal: "
        f"http://{host}:{port}"
    )
    print("Broker Write: OFF")
    print("Order Submission: OFF")
    print("Order Cancel: OFF")
    server.serve_forever()
