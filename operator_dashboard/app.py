from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .console_readers import OperationConsoleReaders
from .readers import DashboardReaders
from .state import StateStore


ALLOWED_ACTIONS = {
    "START",
    "PAUSE",
    "RESUME",
    "STOP",
    "EMERGENCY_STOP",
    "RESET_EMERGENCY_STOP",
}


class DashboardApplication:
    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.state_store = StateStore(
            self.root / "runtime/operator_dashboard/operator_state.json"
        )
        self.readers = DashboardReaders(self.root)
        self.console = OperationConsoleReaders(self.root)

    def status_payload(self) -> dict[str, Any]:
        operator = self.state_store.load().to_dict()
        return {
            "operator": operator,
            "phases": self.readers.phase_status(),
            "ai": self.readers.ai_status(),
            "paper": self.readers.paper_status(),
            "positions": self.readers.positions(),
            "risk": self.readers.risk(),
            "logs": self.readers.logs(),
            "operation_console": {
                "ai_candidates": self.console.ai_candidates(),
                "watchlist": self.console.watchlist(),
                "orders": self.console.order_history(),
                "fills": self.console.fills(),
                "account_summary": self.console.account_summary(),
                "session_stage": self.console.session_stage(operator),
            },
            "safety": {
                "paper_broker": "ALPACA",
                "live_broker": "ETRADE",
                "live_write_enabled": False,
                "live_cancel_enabled": False,
                "live_allocation_enabled": False,
                "multi_account_enabled": False,
                "runtime_account_switch_enabled": False,
            },
        }

    def health_payload(self) -> dict[str, Any]:
        return {
            "status": "PASS",
            "dashboard": "OPERATOR_DASHBOARD_1_1",
            "paper_broker": "ALPACA",
            "live_broker": "ETRADE",
            "live_write_enabled": False,
        }

    def action_payload(self, action: str) -> tuple[int, dict[str, Any]]:
        action = action.upper()
        if action not in ALLOWED_ACTIONS:
            return HTTPStatus.BAD_REQUEST, {
                "status": "ERROR",
                "error": "INVALID_ACTION",
            }

        state = self.state_store.apply_action(action)
        return HTTPStatus.OK, {
            "status": "PASS",
            "action": action,
            "operator": state.to_dict(),
            "live_write_enabled": False,
        }

    def _binary_file(self, relative: str) -> bytes:
        return (self.root / relative).read_bytes()

    def handler_class(self):
        application = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "OperatorDashboard/1.1"

            def log_message(self, format: str, *args) -> None:
                return

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                data = json.dumps(
                    payload, ensure_ascii=False, sort_keys=True
                ).encode("utf-8")
                self.send_response(status)
                self.send_header(
                    "Content-Type", "application/json; charset=utf-8"
                )
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def _send_bytes(
                self,
                status: int,
                content_type: str,
                data: bytes,
            ) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                path = urlparse(self.path).path
                if path == "/":
                    self._send_bytes(
                        HTTPStatus.OK,
                        "text/html; charset=utf-8",
                        application._binary_file(
                            "operator_dashboard/templates/index.html"
                        ),
                    )
                elif path == "/static/dashboard.css":
                    self._send_bytes(
                        HTTPStatus.OK,
                        "text/css; charset=utf-8",
                        application._binary_file(
                            "operator_dashboard/static/dashboard.css"
                        ),
                    )
                elif path == "/static/dashboard.js":
                    self._send_bytes(
                        HTTPStatus.OK,
                        "application/javascript; charset=utf-8",
                        application._binary_file(
                            "operator_dashboard/static/dashboard.js"
                        ),
                    )
                elif path == "/api/status":
                    self._send_json(
                        HTTPStatus.OK,
                        application.status_payload(),
                    )
                elif path == "/api/health":
                    self._send_json(
                        HTTPStatus.OK,
                        application.health_payload(),
                    )
                else:
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {"status": "ERROR", "error": "NOT_FOUND"},
                    )

            def do_POST(self) -> None:
                path = urlparse(self.path).path
                if path != "/api/action":
                    self._send_json(
                        HTTPStatus.NOT_FOUND,
                        {"status": "ERROR", "error": "NOT_FOUND"},
                    )
                    return

                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    payload = json.loads(
                        self.rfile.read(length).decode("utf-8")
                    )
                except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"status": "ERROR", "error": "INVALID_JSON"},
                    )
                    return

                status, body = application.action_payload(
                    str(payload.get("action", ""))
                )
                self._send_json(status, body)

        return Handler


def create_app(project_root: Path | None = None) -> DashboardApplication:
    root = (
        project_root.resolve()
        if project_root is not None
        else Path(__file__).resolve().parents[1]
    )
    return DashboardApplication(root)


def serve(
    project_root: Path,
    host: str = "127.0.0.1",
    port: int = 8899,
) -> None:
    app = create_app(project_root)
    server = ThreadingHTTPServer((host, port), app.handler_class())
    server.serve_forever()
