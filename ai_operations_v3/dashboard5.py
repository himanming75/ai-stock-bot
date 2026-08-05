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
<title>AI Stock Bot Dashboard 5.0</title>
<style>
body{font-family:Arial,sans-serif;background:#0b0f14;color:#edf3f8;margin:0;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{background:#151b23;border:1px solid #2d3744;border-radius:12px;padding:14px}
.ok{color:#71e5a0}.bad{color:#ff8f8f}.muted{color:#a9b6c6;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:8px;border-bottom:1px solid #303a47;text-align:left}
.bar{height:10px;background:#26303d;border-radius:5px;overflow:hidden}.bar span{display:block;height:100%;background:#6aa7ff}
pre{white-space:pre-wrap;word-break:break-word;max-height:350px;overflow:auto}
.section{margin-top:14px}
</style>
</head>
<body>
<h1>AI Stock Bot Dashboard 5.0</h1>
<div class="muted">Read-only · AI Lab · Strategy Marketplace · Portfolio Intelligence</div>
<div id="root">Loading...</div>
<script>
const esc=v=>String(v??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function load(){
 const d=await fetch('/api/dashboard').then(r=>r.json());
 const m=d.performance_metrics||{}, lab=d.historical_ai_lab||{}, market=d.strategy_marketplace||{}, p=d.portfolio_intelligence||{};
 document.getElementById('root').innerHTML=`
 <div class="grid">
  <div class="card"><h3>System</h3>Status <b class="${d.status==='PASS'?'ok':'bad'}">${esc(d.status)}</b><br>Read only ${esc(d.read_only)}</div>
  <div class="card"><h3>Performance</h3>Win rate ${esc(m.win_rate)}<br>Profit factor ${esc(m.profit_factor)}<br>Sharpe ${esc(m.sharpe_ratio)}</div>
  <div class="card"><h3>Risk</h3>Max drawdown ${esc(m.maximum_drawdown)}<br>Expectancy ${esc(m.expectancy)}</div>
  <div class="card"><h3>AI Lab</h3>Walk-forward windows ${esc(lab.walk_forward_window_count)}<br>Risk of ruin ${esc(lab.monte_carlo_risk_of_ruin)}</div>
  <div class="card"><h3>Strategies</h3>Total ${esc(market.strategy_count)}<br>Enabled ${esc(market.enabled_count)}</div>
  <div class="card"><h3>Portfolio</h3>Value ${esc(p.total_market_value)}<br>Diversification ${esc(p.diversification_score)}</div>
 </div>
 <div class="section card"><h2>Strategy Marketplace</h2><table><tr><th>Strategy</th><th>Category</th><th>Enabled</th><th>Score</th><th>Recommended</th></tr>${(market.strategies||[]).map(x=>`<tr><td>${esc(x.display_name)}</td><td>${esc(x.category)}</td><td>${esc(x.enabled)}</td><td>${esc(x.research_score)}</td><td>${esc(x.recommended)}</td></tr>`).join('')}</table></div>
 <div class="section card"><h2>Sector Allocation</h2>${(p.sector_allocation||[]).map(x=>`<div>${esc(x.sector)} ${esc(x.weight)}<div class="bar"><span style="width:${Math.min(100,Number(x.weight)*100)}%"></span></div></div>`).join('')}</div>
 <div class="section card"><h2>Rebalance Preview</h2><table><tr><th>Symbol</th><th>Current</th><th>Target</th><th>Direction</th></tr>${(p.rebalance_preview||[]).map(x=>`<tr><td>${esc(x.symbol)}</td><td>${esc(x.current_weight)}</td><td>${esc(x.target_weight)}</td><td>${esc(x.suggested_direction)}</td></tr>`).join('')}</table></div>
 <div class="section card"><h2>Raw Dashboard Data</h2><pre>${esc(JSON.stringify(d,null,2))}</pre></div>`;
}
load();setInterval(load,15000);
</script>
</body>
</html>"""


def serve(root: Path, host: str, port: int) -> None:
    dashboard_path = (
        root / "release/v140_to_v143_ai_operations/actual/"
               "dashboard5_data.json"
    )

    class QuietServer(ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            return

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/dashboard":
                body = dashboard_path.read_bytes()
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
    print(f"Dashboard 5.0: http://{host}:{port}")
    server.serve_forever()
