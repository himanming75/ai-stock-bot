from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from .history import (
    fill_history,
    order_history,
    performance_summary,
    position_history,
)
from .metrics import collect_metrics
from .scheduler_monitor import scheduler_status
from .status_reader import collect_status
from .watchdog import evaluate_watchdog


HTML = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Stock Bot Operations</title>
<style>
:root{font-family:Arial,sans-serif;color:#edf2f7;background:#0b0f14}
body{margin:0;padding:22px}.top{display:flex;justify-content:space-between;align-items:center}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.card{background:#151b23;border:1px solid #2c3644;border-radius:12px;padding:15px}
.ok{color:#72e6a6}.bad{color:#ff8e8e}.pending{color:#ffd479}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px;border-bottom:1px solid #303948}
details{margin-top:12px;background:#111720;border:1px solid #2c3644;border-radius:10px;padding:10px}
pre{white-space:pre-wrap;word-break:break-word;font-size:12px;max-height:400px;overflow:auto}
.small{font-size:12px;color:#a9b6c6}.section{margin-top:22px}
</style>
</head>
<body>
<div class="top"><div><h1>AI Stock Bot Operations</h1>
<div class="small">Read-only • Auto refresh every 15 seconds • Live writes unavailable</div></div>
<div id="updated" class="small"></div></div>
<div id="root">Loading...</div>
<script>
const bool=(v)=>v===true?'<b class="ok">PASS</b>':v===false?'<b class="bad">NO</b>':'<b class="pending">PENDING</b>';
const esc=(v)=>String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function rows(items,cols){
 if(!items||!items.length)return '<tr><td colspan="'+cols.length+'" class="small">No records</td></tr>';
 return items.slice(-20).reverse().map(x=>'<tr>'+cols.map(c=>'<td>'+esc(c.get(x))+'</td>').join('')+'</tr>').join('');
}
async function load(){
 const [s,m,w,sch,h]=await Promise.all([
  fetch('/api/status').then(r=>r.json()),
  fetch('/api/metrics').then(r=>r.json()),
  fetch('/api/watchdog').then(r=>r.json()),
  fetch('/api/scheduler').then(r=>r.json()),
  fetch('/api/history').then(r=>r.json())
 ]);
 document.getElementById('updated').textContent='Updated '+new Date().toLocaleTimeString();
 document.getElementById('root').innerHTML=`
 <div class="grid">
  <div class="card"><h3>Mode</h3>Paper ${bool(s.mode.paper)}<br>Live ${bool(s.mode.live)}<br>Live activation ${bool(s.mode.live_activation_allowed)}</div>
  <div class="card"><h3>Kill Switch</h3>Active ${bool(s.kill_switch.kill_switch_active)}<br><span class="small">${esc(s.kill_switch.reason)}</span></div>
  <div class="card"><h3>Actual Validation</h3>P2 ${bool(s.actual_validation.p2.validated)}<br>P3 ${bool(s.actual_validation.p3.validated)}<br>P4 ${bool(s.actual_validation.p4.validated)}</div>
  <div class="card"><h3>Watchdog</h3>Status ${w.status==='PASS'?'<b class="ok">PASS</b>':'<b class="bad">'+esc(w.status)+'</b>'}<br>Heartbeat age ${esc(w.heartbeat_age_seconds)} sec</div>
  <div class="card"><h3>Metrics</h3>Orders ${m.history_counts.order_events}<br>Fills ${m.history_counts.fill_events}<br>Drifts ${m.history_counts.drift_events}<br>Cycles ${m.history_counts.runtime_cycles}</div>
  <div class="card"><h3>Performance</h3>Realized P/L ${esc(h.performance.realized_pnl)}<br>Win rate ${(h.performance.win_rate*100).toFixed(1)}%<br>Max drawdown ${esc(h.performance.maximum_drawdown)}</div>
 </div>
 <div class="section card"><h2>Orders</h2><table><thead><tr><th>Time</th><th>Client ID</th><th>Order ID</th><th>Type</th></tr></thead><tbody>${rows(h.orders,[{get:x=>x.observed_at},{get:x=>x.client_order_id},{get:x=>x.broker_order_id},{get:x=>x.record_type}])}</tbody></table></div>
 <div class="section card"><h2>Fills</h2><table><thead><tr><th>Time</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Price</th></tr></thead><tbody>${rows(h.fills,[{get:x=>x.observed_at},{get:x=>x.symbol},{get:x=>x.side},{get:x=>x.filled_qty},{get:x=>x.filled_avg_price}])}</tbody></table></div>
 <div class="section card"><h2>Positions</h2><table><thead><tr><th>Time</th><th>Symbol</th><th>Qty</th><th>Market Value</th></tr></thead><tbody>${rows(h.positions,[{get:x=>x.observed_at},{get:x=>x.symbol},{get:x=>x.qty},{get:x=>x.market_value}])}</tbody></table></div>
 <details><summary>Scheduler</summary><pre>${esc(JSON.stringify(sch,null,2))}</pre></details>
 <details><summary>Recovery / Watchdog</summary><pre>${esc(JSON.stringify(w,null,2))}</pre></details>
 <details><summary>Raw status</summary><pre>${esc(JSON.stringify(s,null,2))}</pre></details>`;
}
load();setInterval(load,15000);
</script>
</body></html>"""


def build_history(root: Path):
    return {
        "orders": order_history(root),
        "fills": fill_history(root),
        "positions": position_history(root),
        "performance": performance_summary(root),
    }


def serve(root: Path, host: str, port: int) -> None:
    class QuietServer(ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            return

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            endpoints = {
                "/api/status": lambda: collect_status(root),
                "/api/metrics": lambda: collect_metrics(root),
                "/api/watchdog": lambda: evaluate_watchdog(root),
                "/api/scheduler": lambda: scheduler_status(root),
                "/api/history": lambda: build_history(root),
            }
            if path in endpoints:
                body = json.dumps(
                    endpoints[path](),
                    indent=2,
                    sort_keys=True,
                ).encode("utf-8")
                self.send_response(200)
                content_type = "application/json; charset=utf-8"
            elif path in {"/", "/index.html"}:
                body = HTML.encode("utf-8")
                self.send_response(200)
                content_type = "text/html; charset=utf-8"
            else:
                body = b"Not found"
                self.send_response(404)
                content_type = "text/plain; charset=utf-8"

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
    print(f"Dashboard: http://{host}:{port}")
    server.serve_forever()
