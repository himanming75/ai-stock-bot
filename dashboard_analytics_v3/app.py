from __future__ import annotations
import argparse, json, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard_analytics_v3.analytics import collect
from dashboard_analytics_v3.render import render
from dashboard_analytics_v3.io import write_json

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def send(self, body: bytes, content_type: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in {"/", "/index.html"}:
            self.send(render(collect(ROOT)).encode("utf-8"), "text/html; charset=utf-8")
            return
        if self.path == "/api/analytics":
            data = collect(ROOT)
            self.send((json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8"), "application/json")
            return
        if self.path == "/health":
            self.send(b'{"status":"ok","stage":"V90.32"}\n', "application/json")
            return
        self.send(b"Not Found\n", "text/plain", 404)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8602)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("Dashboard Analytics v3 only permits localhost.")
    data = collect(ROOT)
    write_json(ROOT / "release/v90_01_to_v90_32/actual/dashboard_analytics_v3_state.json", data)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"DASHBOARD_URL=http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
