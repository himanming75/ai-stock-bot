from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,sys
ROOT=Path(r"C:\stock-bot")
sys.path.insert(0,str(ROOT))
from unified_audit_v2 import build
HTML="""<!doctype html><html><head><meta charset='utf-8'><meta http-equiv='refresh' content='30'><style>
body{font-family:Arial;background:#0d1117;color:#e6edf3;margin:18px}.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}.c{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px}.b{font-size:28px;font-weight:700}table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #30363d;text-align:left}.s{color:#8b949e;font-size:12px}</style></head><body><h1>Alpaca Paper Operations Dashboard V2</h1><div class='s'>READ ONLY · refresh 30s</div><div id='a'>Loading...</div><script>
async function L(){let d=await(await fetch('/api')).json(),p=d.validation_progress||{},m=d.validation_metrics||{},b=d.broker_snapshot||{},h=d.reliability_health||{},w=d.watchdog||{};let r=(d.recent_timeline||[]).slice(0,20).map(x=>`<tr><td>${x.time||''}</td><td>${x.event_type}</td><td>${x.symbol||''}</td><td>${x.side||''}</td><td>${x.quantity??''}</td><td>${x.realized_pl??''}</td><td>${x.reason||''}</td></tr>`).join('');document.getElementById('a').innerHTML=`<div class='g'><div class='c'>Closed Trades<div class='b'>${p.closed_trades??0}</div></div><div class='c'>Trading Days<div class='b'>${p.trading_days??0}/10</div></div><div class='c'>Gate<div class='b'>${p.gate_status||'COLLECTING_DATA'}</div></div><div class='c'>Health<div class='b'>${h.status||'UNKNOWN'}</div></div><div class='c'>Positions<div class='b'>${b.position_count??0}</div>${(b.position_symbols||[]).join(', ')}</div><div class='c'>Open Orders<div class='b'>${b.open_order_count??0}</div></div><div class='c'>Win Rate<div class='b'>${m.win_rate??'-'}</div></div><div class='c'>Profit Factor<div class='b'>${m.profit_factor??'-'}</div></div></div><h2>Recent Timeline</h2><div class='c'><table><tr><th>Time</th><th>Event</th><th>Symbol</th><th>Side</th><th>Qty</th><th>P/L</th><th>Reason</th></tr>${r||'<tr><td colspan=7>No events yet</td></tr>'}</table></div>`}L();</script></body></html>"""
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/api":
            x=json.dumps(build(ROOT),default=str).encode();self.send_response(200);self.send_header("Content-Type","application/json");self.end_headers();self.wfile.write(x)
        else:
            x=HTML.encode();self.send_response(200);self.send_header("Content-Type","text/html");self.end_headers();self.wfile.write(x)
    def log_message(self,*a): pass
ThreadingHTTPServer(("127.0.0.1",8765),H).serve_forever()
