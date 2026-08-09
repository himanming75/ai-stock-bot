from __future__ import annotations
from pathlib import Path
import argparse

TARGET = Path("dashboard/templates/operations_dashboard_v3_2.html")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()
    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")
    if 'id="analyticsTradeCount"' in text:
        print("V3.5 ANALYTICS HTML ALREADY PRESENT")
        return 0
    timeline_marker = '<div class="section">\n<h3>Recent Timeline</h3>'
    analytics_html = '''<div class="section">
<h3>Historical Performance & Trade Analytics</h3>
<div class="grid">
<div class="card"><h2>Numeric Trades</h2><div id="analyticsTradeCount" class="big"></div><div id="analyticsObserved" class="note"></div></div>
<div class="card"><h2>Net Realized P/L</h2><div id="analyticsNet" class="big"></div></div>
<div class="card"><h2>Win Rate</h2><div id="analyticsWinRate" class="big"></div></div>
<div class="card"><h2>Profit Factor</h2><div id="analyticsPF" class="big"></div></div>
<div class="card"><h2>Average Trade</h2><div id="analyticsAvgTrade" class="big"></div></div>
<div class="card"><h2>Average Win</h2><div id="analyticsAvgWin" class="big"></div></div>
<div class="card"><h2>Average Loss</h2><div id="analyticsAvgLoss" class="big"></div></div>
<div class="card"><h2>Max Realized Drawdown</h2><div id="analyticsDD" class="big"></div></div>
</div>
<div class="two" style="margin-top:12px">
<div><h3>Cumulative Realized P/L</h3><div id="analyticsCumulativeChart" class="chartbox"></div></div>
<div><h3>Historical vs Validation</h3><table><thead><tr><th>Scope</th><th>Status</th><th>Trades</th><th>Net P/L</th><th>Win Rate</th><th>Profit Factor</th></tr></thead><tbody id="analyticsScopeRows"></tbody></table></div>
</div>
<div class="two" style="margin-top:12px">
<div><h3>By Symbol</h3><table><thead><tr><th>Symbol</th><th>Trades</th><th>Net P/L</th><th>Win Rate</th><th>PF</th></tr></thead><tbody id="analyticsSymbolRows"></tbody></table></div>
<div><h3>By Exit Reason</h3><table><thead><tr><th>Reason</th><th>Trades</th><th>Net P/L</th><th>Win Rate</th><th>PF</th></tr></thead><tbody id="analyticsReasonRows"></tbody></table></div>
</div>
<div class="note" id="analyticsStatus"></div>
</div>
'''
    if timeline_marker not in text:
        raise RuntimeError("Recent Timeline marker not found")
    text = text.replace(timeline_marker, analytics_html + timeline_marker, 1)
    source_marker = "  document.getElementById('sources').textContent='Runtime sources: '+d.data_sources.join(' | ');"
    js = '''  let a=d.trade_analytics||{};
  let ah=a.historical||{};
  let av=a.validation||{};
  function pfTextValue(pf){if(pf===null||pf===undefined)return '-';if(String(pf)==='INF')return '∞';let n=Number(pf);return Number.isFinite(n)?n.toFixed(2):'-';}
  setv('analyticsTradeCount',ah.numeric_trade_count??0);
  document.getElementById('analyticsObserved').textContent=`Observed closed trades: ${ah.observed_closed_trade_count??0}`;
  setv('analyticsNet',money(ah.net_realized_pnl),Number(ah.net_realized_pnl||0)<0?'FAIL':'PASS');
  setv('analyticsWinRate',pct(ah.win_rate));
  setv('analyticsPF',pfTextValue(ah.profit_factor));
  setv('analyticsAvgTrade',money(ah.average_trade));
  setv('analyticsAvgWin',money(ah.average_win));
  setv('analyticsAvgLoss',money(ah.average_loss),Number(ah.average_loss||0)<0?'FAIL':'PASS');
  setv('analyticsDD',money(ah.max_realized_drawdown));
  document.getElementById('analyticsCumulativeChart').innerHTML=lineSvg(ah.cumulative_realized_pnl||[]);
  function statRow(label,s){return `<tr><td>${label}</td><td>${s?.data_status||'-'}</td><td>${s?.numeric_trade_count??0}</td><td>${money(s?.net_realized_pnl)}</td><td>${pct(s?.win_rate)}</td><td>${pfTextValue(s?.profit_factor)}</td></tr>`;}
  document.getElementById('analyticsScopeRows').innerHTML=statRow('Historical',ah)+statRow('Validation',av);
  function groupRows(rows){if(!rows||rows.length===0)return '<tr><td colspan="5">INSUFFICIENT_DATA</td></tr>';return rows.slice(0,12).map(x=>`<tr><td>${x.name||''}</td><td>${x.numeric_trade_count??0}</td><td>${money(x.net_realized_pnl)}</td><td>${pct(x.win_rate)}</td><td>${pfTextValue(x.profit_factor)}</td></tr>`).join('');}
  document.getElementById('analyticsSymbolRows').innerHTML=groupRows(a.by_symbol||[]);
  document.getElementById('analyticsReasonRows').innerHTML=groupRows(a.by_exit_reason||[]);
  document.getElementById('analyticsStatus').textContent=`Analytics: ${d.trade_analytics_status||'UNKNOWN'} | Sources: ${(a.source_ledgers||[]).join(' | ')||'none'}`;
'''
    if source_marker not in text:
        raise RuntimeError("sources JS marker not found")
    text = text.replace(source_marker, js + source_marker, 1)
    text = text.replace("Alpaca Paper · Read-only · V3.4 Visualization Layer", "Alpaca Paper · Read-only · V3.5 Trade Analytics", 1)
    target.write_text(text, encoding="utf-8")
    print("V3.5 ANALYTICS HTML PATCH: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
