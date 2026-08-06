from __future__ import annotations
import json
from http import HTTPStatus
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from urllib.parse import urlparse

from .io import read_json


STATIC_ROOT = (
    Path(__file__).resolve().parent / "static"
)


class DashboardHandler(BaseHTTPRequestHandler):
    data_root: Path | None = None

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

    def _data(self) -> dict:
        root = self.data_root
        return {
            "certification": read_json(
                root.parent
                / "phase1_premarket_completion_certification.json"
            ),
            "report": read_json(
                root
                / "phase1_premarket_report_bilingual.json"
            ),
            "health": read_json(
                root / "health_score.json"
            ),
            "session": read_json(
                root / "session_plan.json"
            ),
            "runtime": read_json(
                root / "runtime_load_plan.json"
            ),
            "backup": read_json(
                root / "backup_plan.json"
            ),
            "notification": read_json(
                root / "notification_preview.json"
            ),
            "command": read_json(
                root / "latest_command_plan.json"
            ),
        }

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
                        "status_ko": "정상",
                        "mode": "READ_ONLY",
                        "broker_write_enabled": False,
                    },
                )
                return
            if path == "/api/dashboard":
                self._json(
                    HTTPStatus.OK,
                    self._data(),
                )
                return
            self._json(
                HTTPStatus.NOT_FOUND,
                {
                    "error": "NOT_FOUND",
                    "error_ko": (
                        "요청한 경로를 찾을 수 없습니다"
                    ),
                },
            )
        except Exception as exc:
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "error": str(exc),
                    "error_ko": (
                        "서버 처리 중 오류가 발생했습니다"
                    ),
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
    data_root: Path,
    host: str = "127.0.0.1",
    port: int = 8771,
) -> None:
    DashboardHandler.data_root = data_root
    server = ThreadingHTTPServer(
        (host, port),
        DashboardHandler,
    )
    print(
        "Phase 1 Premarket Completion Dashboard / "
        "1단계 장전 완료 대시보드: "
        f"http://{host}:{port}"
    )
    print("Read Only / 조회 전용")
    print("Broker Write OFF / 브로커 주문 차단")
    print("Order Submission OFF / 주문 제출 차단")
    server.serve_forever()
