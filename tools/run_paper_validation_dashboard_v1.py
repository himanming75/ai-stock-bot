from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from paper_validation_ops import ValidationOperationsService

HTML = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="30">
<title>Paper Validation Operations</title>
<style>
body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:20px}
h1,h2{margin:8px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.card{background:#1b1b1b;border:1px solid #333;border-radius:10px;padding:14px}
.big{font-size:30px;font-weight:700}.muted{color:#aaa}.ok{color:#8ee28e}.warn{color:#ffd166}
table{width:100%;border-collapse:collapse}th,td{border-bottom:1px solid #333;padding:8px;text-align:left}
code{white-space:pre-wrap}
</style>
</head>
<body>
<h1>Alpaca Paper Validation Operations</h1>
<div class="muted">READ ONLY · trading configuration is not changed · refresh 30s</div>
<div id="app">Loading...</div>
<script>
async function load(){
 const r=await fetch('/api/report'); const d=await r.json();
 const p=d.progress||{}, m=d.metrics||{}, o=d.operational||{}, t=o.paper_task||{};
 let daily=(d.daily_breakdown||[]).slice(-10).map(x=>`<tr><td>${x.date}</td><td>${x.closed_trades}</td><td>${x.realized_pl??''}</td></tr>`).join('');
 let syms=(d.symbol_breakdown||[]).slice(0,10).map(x=>`<tr><td>${x.symbol}</td><td>${x.trades}</td><td>${x.win_rate}</td><td>${x.realized_pl}</td></tr>`).join('');
 document.getElementById('app').innerHTML=`
 <div class="grid">
  <div class="card"><div class="muted">Closed Trades</div><div class="big">${p.closed_trades??0}</div><div>Minimum 200: ${p.closed_trade_minimum_progress_pct??0}%</div><div>Target 300: ${p.closed_trade_target_progress_pct??0}%</div></div>
  <div class="card"><div class="muted">Trading Days</div><div class="big">${p.trading_days??0}/10</div><div>${p.trading_day_progress_pct??0}%</div></div>
  <div class="card"><div class="muted">Gate</div><div class="big ${p.gate_status==='PAPER_VALIDATION_MINIMUM_GATE_PASSED'?'ok':'warn'}">${p.gate_status||''}</div></div>
  <div class="card"><div class="muted">Paper Task</div><div class="big">${t.State||'UNKNOWN'}</div><div>Next: ${t.NextRunTime||''}</div></div>
  <div class="card"><div class="muted">Win Rate</div><div class="big">${m.win_rate??'-'}</div></div>
  <div class="card"><div class="muted">Profit Factor</div><div class="big">${m.profit_factor??'-'}</div></div>
  <div class="card"><div class="muted">Expectancy</div><div class="big">${m.expectancy??'-'}</div></div>
  <div class="card"><div class="muted">Max Drawdown $</div><div class="big">${m.max_drawdown_dollars??0}</div></div>
 </div>
 <h2>Last 10 Trading Days</h2>
 <div class="card"><table><tr><th>Date</th><th>Closed Trades</th><th>Realized P/L</th></tr>${daily}</table></div>
 <h2>Symbol Breakdown</h2>
 <div class="card"><table><tr><th>Symbol</th><th>Trades</th><th>Win Rate</th><th>P/L</th></tr>${syms}</table></div>
 <h2>Checks</h2><div class="card"><code>${JSON.stringify(d.checks,null,2)}</code></div>
 <h2>Daily Session</h2><div class="card"><code>${JSON.stringify(o.daily_session||{},null,2)}</code></div>
 `;
}
load();
</script>
</body>
</html>"""

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root", default=".")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args=p.parse_args()
    root=Path(args.repository_root).resolve()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, content_type, body):
            raw=body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control","no-store")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path in ("/","/index.html"):
                return self._send(200,"text/html; charset=utf-8",HTML)
            if self.path.startswith("/api/report"):
                report=ValidationOperationsService(root).build()
                return self._send(
                    200,"application/json; charset=utf-8",
                    json.dumps(report,ensure_ascii=False,default=str)
                )
            return self._send(404,"text/plain; charset=utf-8","Not Found")

        def log_message(self, fmt, *args):
            pass

    server=ThreadingHTTPServer((args.host,args.port),Handler)
    print(f"READ-ONLY DASHBOARD: http://{args.host}:{args.port}")
    server.serve_forever()

if __name__=="__main__":
    main()
