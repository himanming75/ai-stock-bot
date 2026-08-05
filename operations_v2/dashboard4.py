from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from .io import read_json


HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Stock Bot Operations V2</title>
<style>
body{font-family:Arial,sans-serif;background:#0b0f14;color:#eef3f8;margin:0;padding:22px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.card{background:#151b23;border:1px solid #2b3542;border-radius:12px;padding:15px}
.ok{color:#70e6a0}.bad{color:#ff9090}.muted{color:#a9b5c4;font-size:12px}
pre{white-space:pre-wrap;word-break:break-word;max-height:420px;overflow:auto}
table{width:100%;border-collapse:collapse}th,td{padding:8px;border-bottom:1px solid #2e3744;text-align:left}
</style>
</head>
<body>
<h1>AI Stock Bot Operations V2</h1>
<div class="muted">Read-only · Offline operator tools · No broker actions</div>
<div id="root">Loading...</div>
<script>
const esc=v=>String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function load(){
 const [s,q,r,c]=await Promise.all([
  fetch('/api/status').then(x=>x.json()),
  fetch('/api/data-quality').then(x=>x.json()),
  fetch('/api/replay').then(x=>x.json()),
  fetch('/api/config-audit').then(x=>x.json())
 ]);
 document.getElementById('root').innerHTML=`
 <div class="grid">
 <div class="card"><h3>System</h3>Status <b class="${s.status==='PASS'?'ok':'bad'}">${esc(s.status)}</b><br>Release candidate ${esc(s.release_candidate_ready)}</div>
 <div class="card"><h3>Data Quality</h3>Status <b class="${q.status==='PASS'?'ok':'bad'}">${esc(q.status)}</b><br>Bars ${esc(q.bar_count)}</div>
 <div class="card"><h3>Replay</h3>Events ${esc(r.event_count)}<br>Orders created ${esc(r.actual_orders_created)}</div>
 <div class="card"><h3>Config Audit</h3>Changes ${esc(c.change_count)}<br>Protected changes ${esc(c.protected_change_count)}</div>
 </div>
 <div class="card" style="margin-top:14px"><h2>Replay Events</h2><table><tr><th>Time</th><th>Price</th><th>Action</th></tr>${(r.events||[]).slice(-20).reverse().map(e=>`<tr><td>${esc(e.timestamp)}</td><td>${esc(e.price)}</td><td>${esc(e.action)}</td></tr>`).join('')}</table></div>
 <div class="card" style="margin-top:14px"><h2>Raw Status</h2><pre>${esc(JSON.stringify(s,null,2))}</pre></div>`;
}
load();setInterval(load,15000);
</script>
</body>
</html>"""


def serve(root: Path, host: str, port: int) -> None:
    actual = root / "release/operations_v2/actual"

    class QuietServer(ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            return

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            mapping = {
                "/api/status": actual / "operations_v2_result.json",
                "/api/data-quality": actual / "data_quality_result.json",
                "/api/replay": actual / "replay_result.json",
                "/api/config-audit": actual / "config_audit_result.json",
                "/api/daily-report": actual / "daily_operator_report.json",
            }

            if path in mapping:
                body = json.dumps(
                    read_json(mapping[path]),
                    indent=2,
                    sort_keys=True,
                ).encode("utf-8")
                content_type = "application/json; charset=utf-8"
                self.send_response(200)
            elif path in {"/", "/index.html"}:
                body = HTML.encode("utf-8")
                content_type = "text/html; charset=utf-8"
                self.send_response(200)
            else:
                body = b"Not found"
                content_type = "text/plain; charset=utf-8"
                self.send_response(404)

            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                pass

        def log_message(self, format, *args):
            return

    server = QuietServer((host, port), Handler)
    print(f"Operations V2 Dashboard: http://{host}:{port}")
    server.serve_forever()
