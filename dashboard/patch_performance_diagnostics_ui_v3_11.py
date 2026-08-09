
from pathlib import Path
import argparse

TARGET = Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION = '''<div class="section" id="diagnosticsSection">
<h3>Canonical Performance Diagnostics / 정식 거래 성과 진단</h3>
<div class="grid">
<div class="card"><h2>Sample Status / 표본 상태</h2><div id="diagSampleStatus" class="big"></div><div id="diagSampleCount" class="note"></div></div>
<div class="card"><h2>Best Trade / 최고 거래</h2><div id="diagBestTrade" class="big"></div><div id="diagBestMeta" class="note"></div></div>
<div class="card"><h2>Worst Trade / 최저 거래</h2><div id="diagWorstTrade" class="big"></div><div id="diagWorstMeta" class="note"></div></div>
<div class="card"><h2>Average Holding / 평균 보유시간</h2><div id="diagAvgHold" class="big"></div></div>
<div class="card"><h2>Win Streak / 연속 수익</h2><div id="diagWinStreak" class="big"></div></div>
<div class="card"><h2>Loss Streak / 연속 손실</h2><div id="diagLossStreak" class="big"></div></div>
</div>
<div class="two" style="margin-top:12px">
<div><h3>Symbol Diagnostics / 종목별 진단</h3><table><thead><tr><th>Symbol / 종목</th><th>Trades / 거래수</th><th>Net P/L / 순손익</th><th>Win Rate / 승률</th><th>Avg Hold / 평균 보유</th><th>Sample / 표본</th></tr></thead><tbody id="diagSymbolRows"></tbody></table></div>
<div><h3>Exit Reason Diagnostics / 청산사유별 진단</h3><table><thead><tr><th>Reason / 사유</th><th>Trades / 거래수</th><th>Net P/L / 순손익</th><th>Win Rate / 승률</th><th>Avg Hold / 평균 보유</th><th>Sample / 표본</th></tr></thead><tbody id="diagReasonRows"></tbody></table></div>
</div>
<div style="margin-top:12px"><h3>Daily Diagnostics / 날짜별 진단</h3><table><thead><tr><th>Date / 날짜</th><th>Trades / 거래수</th><th>Net P/L / 순손익</th><th>Win Rate / 승률</th><th>Sample / 표본</th></tr></thead><tbody id="diagDateRows"></tbody></table></div>
<div class="card" style="margin-top:12px"><h2>Diagnostic Notes / 진단 메모</h2><div id="diagNotes" class="note"></div></div>
</div>'''

JS = r'''function diagHold(minutes){
  if(minutes===null||minutes===undefined)return '-';
  let m=Number(minutes); if(!Number.isFinite(m))return '-';
  if(m<60)return m.toFixed(1)+' min';
  return Math.floor(m/60)+'h '+Math.round(m%60)+'m';
}
function diagStatusText(status){
  return status==='PASS_SAMPLE'?'PASS SAMPLE / 표본 충족':'INSUFFICIENT SAMPLE / 표본 부족';
}
function diagTradeText(t){
  if(!t)return '-'; let p=Number(t.pnl); return Number.isFinite(p)?money(p):'-';
}
function diagMeta(t){
  if(!t)return '-';
  return (t.symbol||'UNKNOWN')+' | '+(t.reason||'UNKNOWN')+' | '+(t.exit_time||t.time||'');
}
function diagGroupRows(rows,withDate){
  return (rows||[]).map(r=>'<tr><td>'+(r.name||'UNKNOWN')+'</td><td>'+(r.numeric_trade_count??r.trade_count??0)+'</td><td>'+(r.net_realized_pnl===null||r.net_realized_pnl===undefined?'-':money(r.net_realized_pnl))+'</td><td>'+(r.win_rate===null||r.win_rate===undefined?'-':pct(r.win_rate))+'</td>'+(withDate?'':'<td>'+diagHold(r.average_holding_minutes)+'</td>')+'<td>'+diagStatusText(r.sample_status)+'</td></tr>').join('');
}
function loadDiagnostics(d){
  let diag=((d.trade_analytics||{}).performance_diagnostics)||{};
  let pass=diag.status==='PASS_SAMPLE';
  setv('diagSampleStatus',diagStatusText(diag.status),pass?'PASS':'WAIT');
  setv('diagSampleCount',(diag.canonical_numeric_trade_count??0)+' / '+(diag.minimum_sample_required??10)+' canonical trades / 정식 거래');
  setv('diagBestTrade',diagTradeText(diag.best_trade),'PASS');
  setv('diagBestMeta',diagMeta(diag.best_trade));
  setv('diagWorstTrade',diagTradeText(diag.worst_trade),diag.worst_trade&&Number(diag.worst_trade.pnl)<0?'FAIL':'PASS');
  setv('diagWorstMeta',diagMeta(diag.worst_trade));
  setv('diagAvgHold',diagHold(diag.average_holding_minutes));
  setv('diagWinStreak',(diag.streaks||{}).max_consecutive_wins??0);
  setv('diagLossStreak',(diag.streaks||{}).max_consecutive_losses??0);
  document.getElementById('diagSymbolRows').innerHTML=diagGroupRows(diag.by_symbol,false)||'<tr><td colspan="6">No data / 데이터 없음</td></tr>';
  document.getElementById('diagReasonRows').innerHTML=diagGroupRows(diag.by_exit_reason,false)||'<tr><td colspan="6">No data / 데이터 없음</td></tr>';
  document.getElementById('diagDateRows').innerHTML=diagGroupRows(diag.by_date,true)||'<tr><td colspan="5">No data / 데이터 없음</td></tr>';
  let notes=(diag.notes||[]);
  document.getElementById('diagNotes').innerHTML=notes.length?notes.map(n=>'<div>- '+n+'</div>').join(''):'No diagnostic warnings / 진단 경고 없음';
}
async function refreshDiagnostics(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let data=await response.json(); loadDiagnostics(data);
  }catch(error){
    let e=document.getElementById('diagNotes');
    if(e)e.textContent='Diagnostics load error / 진단 로드 오류: '+error;
  }
}
document.addEventListener('DOMContentLoaded',()=>{refreshDiagnostics();setInterval(refreshDiagnostics,30000);});'''

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()
    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if 'id="diagnosticsSection"' in text:
        print("V3.11 DIAGNOSTICS UI ALREADY PRESENT")
        return 0

    marker = '<div class="section" id="tradeDetailSection">\n<h3>Canonical Trade Detail & Lifecycle Matrix / 정식 거래 상세 및 라이프사이클</h3>\n'
    if marker not in text:
        raise RuntimeError("V3.11 TRADE DETAIL INSERT MARKER NOT FOUND")
    text = text.replace(marker, SECTION + "\n" + marker, 1)

    if "</script>" not in text:
        raise RuntimeError("V3.11 SCRIPT END MARKER NOT FOUND")
    text = text.replace("</script>", JS + "\n</script>", 1)
    text = text.replace(
        "V3.10 Canonical Trade Detail / 정식 거래 상세",
        "V3.11 Performance Diagnostics / 거래 성과 진단",
        1,
    )
    target.write_text(text, encoding="utf-8")
    print("V3.11 BILINGUAL DIAGNOSTICS UI: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
