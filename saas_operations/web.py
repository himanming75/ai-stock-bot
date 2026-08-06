from __future__ import annotations
import json
import time
from http import HTTPStatus
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import urlparse

from .dashboard import build_dashboard
from .health import HeartbeatRegistry, system_health
from .logs import list_logs
from .metrics import MetricsRegistry
from .notifications import NotificationQueue


STATIC_ROOT = Path(__file__).resolve().parent / "static"


class OperationsRequestHandler(BaseHTTPRequestHandler):
    metrics: MetricsRegistry | None = None
    heartbeats: HeartbeatRegistry | None = None
    notifications: NotificationQueue | None = None
    runtime_root: Path | None = None
    backup_items: list[dict] = []

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
        raw = (STATIC_ROOT / filename).read_bytes()
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
        started = time.perf_counter()
        path = urlparse(self.path).path
        status = HTTPStatus.OK
        try:
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
                        "service": "saas_operations",
                        "broker_write_enabled": False,
                        "order_submission_enabled": False,
                    },
                )
                return
            if path == "/api/dashboard":
                dashboard = build_dashboard(
                    metrics=self.metrics,
                    heartbeats=self.heartbeats,
                    system=system_health(
                        runtime_path=self.runtime_root
                    ),
                    notifications=(
                        self.notifications.list_items()
                    ),
                    logs=list_logs(
                        self.runtime_root
                    ),
                    backups=self.backup_items,
                )
                self._json(
                    HTTPStatus.OK,
                    dashboard,
                )
                return

            status = HTTPStatus.NOT_FOUND
            self._json(
                status,
                {"error": "NOT_FOUND"},
            )
        except Exception as exc:
            status = HTTPStatus.BAD_REQUEST
            self._json(
                status,
                {"error": str(exc)},
            )
        finally:
            elapsed = (
                time.perf_counter() - started
            ) * 1000
            self.metrics.record_request(
                route=path,
                latency_ms=elapsed,
                status_code=int(status),
            )


def serve(
    *,
    metrics: MetricsRegistry,
    heartbeats: HeartbeatRegistry,
    notifications: NotificationQueue,
    runtime_root: Path,
    backup_items: list[dict],
    host: str = "127.0.0.1",
    port: int = 8767,
) -> None:
    OperationsRequestHandler.metrics = metrics
    OperationsRequestHandler.heartbeats = heartbeats
    OperationsRequestHandler.notifications = notifications
    OperationsRequestHandler.runtime_root = runtime_root
    OperationsRequestHandler.backup_items = backup_items
    server = ThreadingHTTPServer(
        (host, port),
        OperationsRequestHandler,
    )
    print(
        f"SaaS Operations Console: http://{host}:{port}"
    )
    server.serve_forever()
