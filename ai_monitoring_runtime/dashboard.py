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
<title>AI Monitoring Dashboard</title>
<style>
body{font-family:Arial,sans-serif;background:#0b0f14;color:#edf3f8;margin:0;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{background:#151b23;border:1px solid #2d3744;border-radius:12px;padding:14px}
.ok{color:#72e5a0}.bad{color:#ff8f8f}.muted{color:#a9b6c6;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px;border-bottom:1px solid #303a47;text-align:left}
pre{white-space:pre-wrap;word-break:break-word;max-height:380px;overflow:auto}
</style>
</head>
<body>
<h1>AI Monitoring Dashboard</h1>
<div class="muted">Read-only · Offline workers · No broker or order actions</div>
<div id="root">Loading...</div>
<script>
const esc=v=>String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function load(){
 const d=await fetch('/api/status').then(r=>r.json());
 const m=d.metrics||{}, h=d.runtime_health||{}, l=d.load_balance||{};
 document.getElementById('root').innerHTML=`
 <div class="grid">
  <div class="card"><h3>System</h3>Status <b class="${d.status==='PASS'?'ok':'bad'}">${esc(d.status)}</b><br>Release gate ${esc(m.release_gate)}</div>
  <div class="card"><h3>Shadow Portfolio</h3>Equity ${esc(m.shadow_equity)}<br>Realized ${esc(m.shadow_realized_pnl)}<br>Unrealized ${esc(m.shadow_unrealized_pnl)}</div>
  <div class="card"><h3>AI</h3>Ensemble ${esc(m.ensemble_score)}<br>Signal ${esc(m.ensemble_signal)}</div>
  <div class="card"><h3>Risk</h3>State ${esc(m.shadow_risk_state)}<br>Drawdown ${esc(m.maximum_drawdown)}</div>
  <div class="card"><h3>Workers</h3>Completed ${esc(h.completed_tasks)}<br>Failed ${esc(h.failed_tasks)}</div>
  <div class="card"><h3>Load Balance</h3>Balanced ${esc(l.balanced)}<br>Imbalance ${esc(l.maximum_task_imbalance)}</div>
 </div>
 <div class="card" style="margin-top:14px"><h2>Worker Results</h2><table><tr><th>Worker</th><th>Symbol</th><th>Strategy</th><th>Score</th><th>State</th></tr>${(d.worker_results||[]).map(x=>`<tr><td>${esc(x.worker_id)}</td><td>${esc(x.symbol)}</td><td>${esc(x.strategy_id)}</td><td>${esc(x.scan_score)}</td><td>${esc(x.scan_state)}</td></tr>`).join('')}</table></div>
 <div class="card" style="margin-top:14px"><h2>Raw Status</h2><pre>${esc(JSON.stringify(d,null,2))}</pre></div>`;
}
load();setInterval(load,15000);
</script>
</body>
</html>"""


def serve(root: Path, host: str, port: int) -> None:
    status_path = (
        root / "release/ai_monitoring_distributed_runtime/actual/"
               "ai_monitoring_distributed_runtime_result.json"
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
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def log_message(self, format, *args):
            return

    server = QuietServer((host, port), Handler)
    print(f"AI Monitoring Dashboard: http://{host}:{port}")
    server.serve_forever()
