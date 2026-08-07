from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,sys
ROOT=Path(r"C:\stock-bot")
sys.path.insert(0,str(ROOT))
from unified_audit_v2 import build

HTML="""<!doctype html><html><head><meta charset='utf-8'><meta http-equiv='refresh' content='30'>
<style>
body{font-family:Arial;background:#0d1117;color:#e6edf3;margin:18px}.g{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px}
.c{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px}.b{font-size:26px;font-weight:700}.ok{color:#3fb950}.bad{color:#f85149}.warn{color:#d29922}
table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #30363d;text-align:left}.s{color:#8b949e;font-size:12px}h2{margin-top:24px}
</style></head><body><h1>Alpaca Paper Operations Dashboard V2</h1>
<div class='s'>READ ONLY · 2-week / 300-trade validation · AI shadow calibration · refresh 30s</div><div id='a'>Loading...</div>
<script>
const fmt=v=>v===null||v===undefined?'-':v;
const pct=v=>v===null||v===undefined?'-':(Number(v)*100).toFixed(1)+'%';
const rows=xs=>(xs||[]).slice(0,12).map(x=>`<tr><td>${x.group||''}</td><td>${x.count??0}</td><td>${pct(x.win_rate)}</td><td>${fmt(x.profit_factor)}</td><td>${fmt(x.expectancy)}</td><td>${fmt(x.total_pl)}</td></tr>`).join('');
async function L(){
let d=await(await fetch('/api')).json(),p=d.validation_progress||{},m=d.validation_metrics||{},h=d.reliability_health||{},
lr=d.live_readiness||{},pb=d.paper_vs_backtest||{},ai=d.ai_outcome_metrics||{},rs=d.ai_research_samples||{},
et=d.etrade_live_readiness||{},vt=d.validation_transition||{};
let recent=(d.ai_linked_trades||[]).slice(-20).reverse().map(x=>`<tr><td>${x.trade_entry_time||''}</td><td>${x.symbol||''}</td><td>${x.ensemble_decision||''}</td><td>${x.market_regime||''}</td><td>${x.confidence_band||''}</td><td>${x.realized_pl??''}</td><td>${x.linked?'YES':'NO'}</td></tr>`).join('');
let cls=lr.eligible?'ok':'warn',ts=vt.transition_state||'NO_OBSERVER_DATA';
let tcls=ts==='PAPER_AUTONOMOUS_ENABLED'?'ok':(ts==='WAITING_FOR_FINALIZER_FLAT_CONFIRMATION'?'warn':'bad');
document.getElementById('a').innerHTML=`
<div class='g'>
<div class='c'>Paper Transition<div class='b ${tcls}'>${ts}</div><div class='s'>Paper ${(vt.paper_task||{}).state||'-'} · Finalizer ${(vt.finalizer_task||{}).state||'-'}</div></div>
<div class='c'>Closed Trades<div class='b'>${p.closed_trades??0}/300</div><div class='s'>${p.closed_trade_target_progress_pct??0}%</div></div>
<div class='c'>Trading Days<div class='b'>${p.trading_days??0}/10</div><div class='s'>${p.trading_day_target_progress_pct??0}%</div></div>
<div class='c'>Win Rate<div class='b'>${pct(m.win_rate)}</div></div>
<div class='c'>Profit Factor<div class='b'>${fmt(m.profit_factor)}</div></div>
<div class='c'>Expectancy<div class='b'>${fmt(m.expectancy)}</div></div>
<div class='c'>Realized P/L<div class='b'>${fmt(m.total_pl)}</div></div>
<div class='c'>AI Research Samples<div class='b'>${rs.sample_count??0}</div></div>
<div class='c'>AI ↔ Trade Links<div class='b'>${ai.linked_trade_count??0}</div><div class='s'>Link rate ${pct(ai.link_rate)}</div></div>
<div class='c'>Health<div class='b'>${fmt(h.score)}%</div><div class='s'>${h.status||'UNKNOWN'}</div></div>
<div class='c'>Live Readiness<div class='b ${cls}'>${lr.status||'NOT_READY'}</div><div class='s'>Advisory only · never auto-enables live</div></div>
<div class='c'>E*TRADE Stage-1<div class='b warn'>${et.status||'BLOCKED'}</div><div class='s'>Manual arm only · live write OFF</div></div>
</div>
<h2>AI Ensemble Outcome Performance</h2><div class='c'><table><tr><th>Decision</th><th>Trades</th><th>Win Rate</th><th>PF</th><th>Expectancy</th><th>P/L</th></tr>${rows(ai.ensemble_performance)||'<tr><td colspan=6>Collecting data</td></tr>'}</table></div>
<h2>AI Regime Outcome Performance</h2><div class='c'><table><tr><th>Regime</th><th>Trades</th><th>Win Rate</th><th>PF</th><th>Expectancy</th><th>P/L</th></tr>${rows(ai.regime_performance)||'<tr><td colspan=6>Collecting data</td></tr>'}</table></div>
<h2>Symbol Performance</h2><div class='c'><table><tr><th>Symbol</th><th>Trades</th><th>Win Rate</th><th>PF</th><th>Expectancy</th><th>P/L</th></tr>${rows(d.symbol_breakdown)||'<tr><td colspan=6>No trades yet</td></tr>'}</table></div>
<h2>Paper vs Backtest</h2><div class='c'>Status: <b>${pb.status||'COLLECTING_DATA'}</b> · Paper ${pb.paper_trade_count??0} · Backtest ${pb.backtest_trade_count??0}</div>
<h2>Recent AI ↔ Closed-Trade Links</h2><div class='c'><table><tr><th>Entry</th><th>Symbol</th><th>AI Decision</th><th>Regime</th><th>Confidence</th><th>P/L</th><th>Linked</th></tr>${recent||'<tr><td colspan=7>No linked trades yet</td></tr>'}</table></div>`}
L();
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path=="/api":
            x=json.dumps(build(ROOT),default=str).encode()
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(x)
        else:
            x=HTML.encode()
            self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.end_headers(); self.wfile.write(x)
    def log_message(self,*a): pass

ThreadingHTTPServer(("127.0.0.1",8765),H).serve_forever()
