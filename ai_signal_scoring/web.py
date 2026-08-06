from __future__ import annotations
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


STATIC_ROOT = Path(__file__).resolve().parent / "static"


class Handler(BaseHTTPRequestHandler):
    report_path: Path | None = None
    certification_path: Path | None = None

    def _load(self, path: Path) -> dict:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _json(self, status: int, payload) -> None:
        raw = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _static(self, name: str, content_type: str) -> None:
        raw = (STATIC_ROOT / name).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self._static("index.html", "text/html; charset=utf-8")
        if path == "/styles.css":
            return self._static("styles.css", "text/css; charset=utf-8")
        if path == "/app.js":
            return self._static("app.js", "application/javascript; charset=utf-8")
        if path == "/health":
            return self._json(200, {
                "status": "HEALTHY",
                "status_ko": "정상",
                "mode": "OFFLINE_SCORING_ONLY",
                "broker_write_enabled": False,
                "order_submission_enabled": False,
            })
        if path == "/api/dashboard":
            return self._json(200, {
                "report": self._load(self.report_path),
                "certification": self._load(self.certification_path),
            })
        return self._json(404, {
            "error": "NOT_FOUND",
            "error_ko": "경로를 찾을 수 없습니다",
        })


def serve(*, report_path: Path, certification_path: Path, host="127.0.0.1", port=8773):
    Handler.report_path = report_path
    Handler.certification_path = certification_path
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"AI Ensemble Dashboard / AI 앙상블 대시보드: http://{host}:{port}")
    print("Offline Scoring Only / 오프라인 점수 전용")
    print("Broker Write OFF / 브로커 주문 차단")
    print("Order Submission OFF / 주문 제출 차단")
    server.serve_forever()
