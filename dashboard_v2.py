from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,sys
ROOT=Path(r"C:\stock-bot")
sys.path.insert(0,str(ROOT))
from unified_audit_v2 import build

HTML="""<!doctype html><html><head><meta charset='utf-8'>
<meta http-equiv='refresh' content='30'>
<style>
body{font-family:Arial;background:#0d1117;color:#e6edf3;margin:18px}
.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.c{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px}
.b{font-size:27px;font-weight:700}.ok{color:#3fb950}.bad{color:#f85149}.warn{color:#d29922}
table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #30363d;text-align:left}
.s{color:#8b949e;font-size:12px}h2{margin-top:24px}
</style></head><body>
<h1>Alpaca Paper Operations Dashboard V2</h1>
<div class='s'>READ ONLY · 2-week / 300-trade validation · refresh 30s</div>
<div id='a'>Loading...</div>
<script>
const fmt=v=>v===null||v===undefined?'-':v;
const pct=v=>v===null||v===undefined?'-':(Number(v)*100).toFixed(1)+'%';
const rows=(xs)=> (xs||[]).slice(0,12).map(x=>`<tr><td>${x.group||''}</td><td>${x.count??0}</td><td>${pct(x.win_rate)}</td><td>${fmt(x.profit_factor)}</td><td>${fmt(x.expectancy)}</td><td>${fmt(x.total_pl)}</td></tr>`).join('');
async function L(){
 let d=await(await fetch('/api')).json(),p=d.validation_progress||{},m=d.validation_metrics||{},
 b=d.broker_snapshot||{},h=d.reliability_health||{},lr=d.live_readiness||{},pb=d.paper_vs_backtest||{};
 let r=(d.recent_timeline||[]).slice(0,20).map(x=>`<tr><td>${x.time||''}</td><td>${x.event_type}</td><td>${x.symbol||''}</td><td>${x.side||''}</td><td>${x.quantity??''}</td><td>${x.realized_pl??''}</td><td>${x.reason||''}</td></tr>`).join('');
 let cls=lr.eligible?'ok':'warn';
 document.getElementById('a').innerHTML=`
 <div class='g'>
 <div class='c'>Closed Trades<div class='b'>${p.closed_trades??0}/300</div><div class='s'>${p.closed_trade_target_progress_pct??0}%</div></div>
 <div class='c'>Trading Days<div class='b'>${p.trading_days??0}/10</div></div>
 <div class='c'>Win Rate<div class='b'>${pct(m.win_rate)}</div></div>
 <div class='c'>Profit Factor<div class='b'>${fmt(m.profit_factor)}</div></div>
 <div class='c'>Expectancy<div class='b'>${fmt(m.expectancy)}</div></div>
 <div class='c'>Realized P/L<div class='b'>${fmt(m.total_pl)}</div></div>
 <div class='c'>Max Drawdown<div class='b'>${fmt(m.max_drawdown)}</div></div>
 <div class='c'>Loss Streak<div class='b'>${fmt(m.max_loss_streak)}</div></div>
 <div class='c'>Health<div class='b'>${fmt(h.score)}%</div><div class='s'>${h.status||'UNKNOWN'}</div></div>
 <div class='c'>Positions<div class='b'>${b.position_count??0}</div><div class='s'>${(b.position_symbols||[]).join(', ')}</div></div>
 <div class='c'>Open Orders<div class='b'>${b.open_order_count??0}</div></div>
 <div class='c'>Live Readiness<div class='b ${cls}'>${lr.status||'NOT_READY'}</div><div class='s'>Advisory only · never auto-enables live</div></div>
 </div>
 <h2>Symbol Performance</h2><div class='c'><table><tr><th>Symbol</th><th>Trades</th><th>Win Rate</th><th>PF</th><th>Expectancy</th><th>P/L</th></tr>${rows(d.symbol_breakdown)||'<tr><td colspan=6>No trades yet</td></tr>'}</table></div>
 <h2>Exit Reason</h2><div class='c'><table><tr><th>Reason</th><th>Trades</th><th>Win Rate</th><th>PF</th><th>Expectancy</th><th>P/L</th></tr>${rows(d.exit_reason_breakdown)||'<tr><td colspan=6>No data yet</td></tr>'}</table></div>
 <h2>Time Bucket (UTC)</h2><div class='c'><table><tr><th>Bucket</th><th>Trades</th><th>Win Rate</th><th>PF</th><th>Expectancy</th><th>P/L</th></tr>${rows(d.time_bucket_breakdown)||'<tr><td colspan=6>No data yet</td></tr>'}</table></div>
 <h2>Confidence Calibration</h2><div class='c'><table><tr><th>Band</th><th>Trades</th><th>Win Rate</th><th>PF</th><th>Expectancy</th><th>P/L</th></tr>${rows(d.confidence_breakdown)||'<tr><td colspan=6>No data yet</td></tr>'}</table></div>
 <h2>Paper vs Backtest</h2><div class='c'>Status: <b>${pb.status||'COLLECTING_DATA'}</b> · Paper trades ${pb.paper_trade_count??0} · Backtest trades ${pb.backtest_trade_count??0}</div>
 <h2>Recent Timeline</h2><div class='c'><table><tr><th>Time</th><th>Event</th><th>Symbol</th><th>Side</th><th>Qty</th><th>P/L</th><th>Reason</th></tr>${r||'<tr><td colspan=7>No events yet</td></tr>'}</table></div>
 `}L();
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/api":
            x=json.dumps(build(ROOT),default=str).encode()
            self.send_response(200);self.send_header("Content-Type","application/json")
            self.end_headers();self.wfile.write(x)
        else:
            x=HTML.encode();self.send_response(200);self.send_header("Content-Type","text/html")
            self.end_headers();self.wfile.write(x)
    def log_message(self,*a): pass

ThreadingHTTPServer(("127.0.0.1",8765),H).serve_forever()
