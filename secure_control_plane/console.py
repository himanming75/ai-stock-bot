from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse


HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Stock Bot Operator Console</title>
<style>
body{font-family:Arial,sans-serif;background:#0b1017;color:#eef3f8;margin:0;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{background:#151d27;border:1px solid #2e3947;border-radius:12px;padding:15px}
.ok{color:#75e6a3}.warn{color:#ffd166}.bad{color:#ff8c8c}
.muted{color:#aab7c6;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px;border-bottom:1px solid #303b49;text-align:left}
pre{white-space:pre-wrap;word-break:break-word;max-height:420px;overflow:auto}
button{padding:9px 12px;margin:4px;border-radius:8px;border:1px solid #536174;background:#202b38;color:#eef3f8}
button[disabled]{opacity:.5}
</style>
</head>
<body>
<h1>Secure Operator Console</h1>
<div class="muted">Read-only local console · All actions are preview-only</div>
<div id="root">Loading...</div>
<script>
const esc=v=>String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function load(){
 const d=await fetch('/api/status').then(r=>r.json());
 const s=d.operational_status||{};
 document.getElementById('root').innerHTML=`
 <div class="grid">
  <div class="card"><h3>P2</h3>Status <b class="${s.p2_status==='PASS'?'ok':'bad'}">${esc(s.p2_status)}</b><br>Validated ${esc(s.p2_validated)}</div>
  <div class="card"><h3>Monitoring</h3>Status ${esc(s.monitoring_status)}<br>Runtime ${esc(s.runtime_health)}</div>
  <div class="card"><h3>Resilience</h3>Status ${esc(s.operational_resilience_status)}</div>
  <div class="card"><h3>Release Gate</h3><b class="warn">${esc(s.release_gate)}</b></div>
  <div class="card"><h3>Broker Write</h3><b class="ok">${esc(s.broker_write_enabled)}</b></div>
  <div class="card"><h3>Automatic Orders</h3><b class="ok">${esc(s.automatic_order_submission_enabled)}</b></div>
 </div>
 <div class="card" style="margin-top:14px">
  <h2>Preview Controls</h2>
  <button disabled>Start Runtime Preview</button>
  <button disabled>Stop Runtime Preview</button>
  <button disabled>Enable Strategy Preview</button>
  <button disabled>Kill Switch Preview</button>
  <p class="muted">Buttons remain disabled because this console is read-only.</p>
 </div>
 <div class="card" style="margin-top:14px">
  <h2>Pending Requests</h2>
  <table><tr><th>Type</th><th>Subject</th><th>State</th><th>Policy</th></tr>
  ${(d.change_requests||[]).map(x=>`<tr><td>${esc(x.request_type)}</td><td>${esc(x.subject)}</td><td>${esc(x.state)}</td><td>${esc(x.policy_pass)}</td></tr>`).join('')}
  </table>
 </div>
 <div class="card" style="margin-top:14px"><h2>Raw Status</h2><pre>${esc(JSON.stringify(d,null,2))}</pre></div>`;
}
load();setInterval(load,15000);
</script>
</body>
</html>"""


def serve(root: Path, host: str, port: int) -> None:
    status_path = (
        root / "release/secure_control_plane_operator_console/actual/"
               "secure_control_plane_result.json"
    )

    class QuietServer(ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            return

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/status":
                body = status_path.read_bytes()
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
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            body = b"CONTROL_PLANE_WRITE_DISABLED"
            self.send_response(405)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    print(f"Secure Operator Console: http://{host}:{port}")
    QuietServer((host, port), Handler).serve_forever()
