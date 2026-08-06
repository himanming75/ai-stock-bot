from __future__ import annotations
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .control_plane import PersistentSaaSControlPlane


STATIC_ROOT = Path(__file__).resolve().parent / "static"


class PersistentSaaSRequestHandler(BaseHTTPRequestHandler):
    control_plane: PersistentSaaSControlPlane | None = None

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

    def _body(self) -> dict:
        length = int(
            self.headers.get("Content-Length", "0")
        )
        if length <= 0:
            return {}
        return json.loads(
            self.rfile.read(length).decode("utf-8")
        )

    def _user(self) -> dict:
        header = self.headers.get(
            "Authorization",
            "",
        )
        if not header.startswith("Bearer "):
            raise PermissionError("AUTH_REQUIRED")
        return self.control_plane.authenticate(
            header.removeprefix("Bearer ").strip()
        )

    def _serve_static(self, filename: str) -> None:
        path = STATIC_ROOT / filename
        if not path.exists():
            self._json(
                HTTPStatus.NOT_FOUND,
                {"error": "NOT_FOUND"},
            )
            return
        raw = path.read_bytes()
        content_type = (
            "text/html; charset=utf-8"
            if filename.endswith(".html")
            else "application/javascript; charset=utf-8"
            if filename.endswith(".js")
            else "text/css; charset=utf-8"
        )
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/health":
                self._json(
                    HTTPStatus.OK,
                    {
                        "status": "HEALTHY",
                        "service": "saas_persistence",
                        "persistent_database": True,
                        "broker_write_enabled": False,
                        "order_submission_enabled": False,
                    },
                )
                return
            if path == "/":
                self._serve_static("index.html")
                return
            if path == "/app.js":
                self._serve_static("app.js")
                return
            if path == "/styles.css":
                self._serve_static("styles.css")
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
                self._json(
                    HTTPStatus.CREATED,
                    self.control_plane.register(
                        email=body["email"],
                        password=body["password"],
                        workspace_name=body[
                            "workspace_name"
                        ],
                    ),
                )
                return

            if path == "/api/login":
                self._json(
                    HTTPStatus.OK,
                    self.control_plane.login(
                        email=body["email"],
                        password=body["password"],
                    ),
                )
                return

            user = self._user()

            if path == "/api/workspaces":
                self._json(
                    HTTPStatus.OK,
                    self.control_plane.list_workspaces(
                        user_id=user["user_id"]
                    ),
                )
                return

            if path == "/api/workspace/summary":
                self._json(
                    HTTPStatus.OK,
                    self.control_plane.workspace_summary(
                        user_id=user["user_id"],
                        workspace_id=body[
                            "workspace_id"
                        ],
                    ),
                )
                return

            if path == "/api/workspace/strategy":
                self._json(
                    HTTPStatus.OK,
                    self.control_plane.update_strategy(
                        user_id=user["user_id"],
                        workspace_id=body[
                            "workspace_id"
                        ],
                        strategy=body["strategy"],
                    ),
                )
                return

            if path == "/api/workspace/risk":
                self._json(
                    HTTPStatus.OK,
                    self.control_plane.update_risk(
                        user_id=user["user_id"],
                        workspace_id=body[
                            "workspace_id"
                        ],
                        risk_profile=body[
                            "risk_profile"
                        ],
                        max_position_weight=float(
                            body["max_position_weight"]
                        ),
                        daily_loss_limit=float(
                            body["daily_loss_limit"]
                        ),
                    ),
                )
                return

            if path == "/api/workspace/member":
                self._json(
                    HTTPStatus.CREATED,
                    self.control_plane.add_member(
                        user_id=user["user_id"],
                        workspace_id=body[
                            "workspace_id"
                        ],
                        member_email=body[
                            "member_email"
                        ],
                        role=body["role"],
                    ),
                )
                return

            if path == "/api/workspace/broker":
                self._json(
                    HTTPStatus.CREATED,
                    self.control_plane.add_broker_metadata(
                        user_id=user["user_id"],
                        workspace_id=body[
                            "workspace_id"
                        ],
                        broker=body["broker"],
                        environment=body[
                            "environment"
                        ],
                        account_alias=body[
                            "account_alias"
                        ],
                    ),
                )
                return

            if path == "/api/workspace/audit":
                self._json(
                    HTTPStatus.OK,
                    self.control_plane.audit_events(
                        user_id=user["user_id"],
                        workspace_id=body[
                            "workspace_id"
                        ],
                    ),
                )
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
    control_plane: PersistentSaaSControlPlane,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    PersistentSaaSRequestHandler.control_plane = (
        control_plane
    )
    server = ThreadingHTTPServer(
        (host, port),
        PersistentSaaSRequestHandler,
    )
    print(
        f"SaaS Persistence: http://{host}:{port}"
    )
    server.serve_forever()
