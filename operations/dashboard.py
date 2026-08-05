from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from .status_reader import collect_status


HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="15">
<title>AI Stock Bot Operations</title>
<style>
body{font-family:Arial,sans-serif;margin:24px;background:#111;color:#eee}
h1,h2{margin-bottom:8px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.card{background:#1d1d1d;border:1px solid #444;border-radius:10px;padding:14px}
.ok{color:#6ee7b7}.bad{color:#fca5a5}.warn{color:#fde68a}
pre{white-space:pre-wrap;word-break:break-word;font-size:12px}
button{padding:8px 12px;margin-right:8px}
</style>
</head>
<body>
<h1>AI Stock Bot Operations Dashboard</h1>
<p>Read-only dashboard. Live activation and broker writes are not available.</p>
<div id="root">Loading...</div>
<script>
async function load(){
 const r=await fetch('/api/status'); const s=await r.json();
 const v=(x)=>x===true?'<span class="ok">TRUE</span>':'<span class="bad">FALSE</span>';
 document.getElementById('root').innerHTML=`
 <div class="grid">
  <div class="card"><h2>Mode</h2>
   Paper: ${v(s.mode.paper)}<br>Live: ${v(s.mode.live)}<br>
   Live activation: ${v(s.mode.live_activation_allowed)}
  </div>
  <div class="card"><h2>Kill Switch</h2>
   Active: ${v(s.kill_switch.kill_switch_active)}<br>
   Reason: ${s.kill_switch.reason||''}
  </div>
  <div class="card"><h2>Actual Validation</h2>
   P2: ${v(s.actual_validation.p2.validated)}<br>
   P3: ${v(s.actual_validation.p3.validated)}<br>
   P4: ${v(s.actual_validation.p4.validated)}
  </div>
  <div class="card"><h2>Completion</h2>
   Paper complete: ${v(s.qualification.paper_complete)}<br>
   Live complete: ${v(s.qualification.live_complete)}
  </div>
 </div>
 <h2>Runtime</h2><pre>${JSON.stringify(s.runtime,null,2)}</pre>
 <h2>Latest Execution / Sync</h2><pre>${JSON.stringify(s.execution,null,2)}</pre>
 <h2>Recent Alerts and Events</h2><pre>${JSON.stringify(s.recent_events,null,2)}</pre>
 <h2>Recent Orders</h2><pre>${JSON.stringify(s.recent_order_events,null,2)}</pre>
 <h2>Recent Fills</h2><pre>${JSON.stringify(s.recent_fill_events,null,2)}</pre>
 <h2>Recent Drift</h2><pre>${JSON.stringify(s.recent_drift_events,null,2)}</pre>`;
}
load();
</script>
</body>
</html>"""


def serve(root: Path, host: str, port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/status":
                body = json.dumps(
                    collect_status(root),
                    indent=2,
                    sort_keys=True,
                ).encode("utf-8")
                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8",
                )
            elif path in {"/", "/index.html"}:
                body = HTML.encode("utf-8")
                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8",
                )
            else:
                body = b"Not found"
                self.send_response(404)
                self.send_header(
                    "Content-Type",
                    "text/plain; charset=utf-8",
                )
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Dashboard: http://{host}:{port}")
    server.serve_forever()
