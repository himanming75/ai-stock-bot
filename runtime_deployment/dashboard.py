from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Stock Bot Dashboard 6.0</title>
<style>
body{font-family:Arial,sans-serif;background:#0a0f15;color:#eef3f7;margin:0;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{background:#151c25;border:1px solid #2e3946;border-radius:12px;padding:14px}
.ok{color:#75e6a3}.warn{color:#ffd166}.bad{color:#ff8f8f}
.muted{color:#a9b6c6;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px;border-bottom:1px solid #303a47;text-align:left}
pre{white-space:pre-wrap;word-break:break-word;max-height:420px;overflow:auto}
</style>
</head>
<body>
<h1>AI Stock Bot Dashboard 6.0</h1>
<div class="muted">Read-only · Runtime service preview · No broker or order actions</div>
<div id="root">Loading...</div>
<script>
const esc=v=>String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function load(){
 const d=await fetch('/api/status').then(r=>r.json());
 const x=d.diagnostics||{}, h=d.runtime_health||{}, s=d.service_preview||{}, b=d.release_bundle||{};
 document.getElementById('root').innerHTML=`
 <div class="grid">
  <div class="card"><h3>System</h3>Status <b class="${d.status==='PASS'?'ok':'bad'}">${esc(d.status)}</b><br>Health ${esc(h.status)}</div>
  <div class="card"><h3>CPU</h3>Logical cores ${esc(x.cpu_logical_count)}</div>
  <div class="card"><h3>Disk</h3>Free ${esc(x.disk_free_bytes)} bytes</div>
  <div class="card"><h3>Service</h3>Installed ${esc(s.service_install_performed)}<br>Started ${esc(s.service_start_performed)}</div>
  <div class="card"><h3>Release</h3>Version ${esc(d.release_version)}<br>Applied ${esc(d.actual_release_applied)}</div>
  <div class="card"><h3>Bundle</h3>Files ${esc(b.file_count)}<br>Size ${esc(b.bundle_size_bytes)}</div>
 </div>
 <div class="card" style="margin-top:14px"><h2>Safety State</h2>
 <table><tr><th>Control</th><th>State</th></tr>
 <tr><td>Broker Write</td><td>${esc(d.actual_broker_write_performed)}</td></tr>
 <tr><td>Order Submission</td><td>${esc(d.actual_order_submission_performed)}</td></tr>
 <tr><td>Automatic Restart</td><td>${esc(d.automatic_restart_enabled)}</td></tr>
 <tr><td>Windows Service Installed</td><td>${esc(d.windows_service_installed)}</td></tr>
 </table></div>
 <div class="card" style="margin-top:14px"><h2>Raw Status</h2><pre>${esc(JSON.stringify(d,null,2))}</pre></div>`;
}
load();setInterval(load,15000);
</script>
</body>
</html>"""


def serve(root: Path, host: str, port: int) -> None:
    status_path = (
        root / "release/runtime_service_deployment/actual/"
               "runtime_service_deployment_result.json"
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
            body = b"DASHBOARD_WRITE_DISABLED"
            self.send_response(405)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    print(f"Dashboard 6.0: http://{host}:{port}")
    QuietServer((host, port), Handler).serve_forever()
