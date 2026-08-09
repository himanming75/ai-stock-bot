
from __future__ import annotations

from pathlib import Path
import argparse

TARGET = Path("dashboard/templates/operations_dashboard_v3_2.html")

CSS = '''
.filterbar{display:flex;flex-wrap:wrap;gap:10px;align-items:end;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px;margin-bottom:10px}
.filteritem{display:flex;flex-direction:column;gap:4px;min-width:150px}
.filteritem label{font-size:11px;color:#8b949e}
.filteritem select,.filteritem input{background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:6px;padding:7px}
.trade-positive{color:#3fb950;font-weight:700}
.trade-negative{color:#f85149;font-weight:700}
.trade-flat{color:#8b949e;font-weight:700}
.scroll-table{overflow-x:auto}
'''

SECTION = '''
<div class="section" id="tradeDetailSection">
<h3>Canonical Trade Detail & Lifecycle Matrix / 정식 거래 상세 및 라이프사이클</h3>
<div class="filterbar">
<div class="filteritem"><label>Date / 날짜</label><select id="tradeFilterDate"><option value="">All / 전체</option></select></div>
<div class="filteritem"><label>Symbol / 종목</label><select id="tradeFilterSymbol"><option value="">All / 전체</option></select></div>
<div class="filteritem"><label>Exit Reason / 청산사유</label><select id="tradeFilterReason"><option value="">All / 전체</option></select></div>
<div class="filteritem"><label>Result / 결과</label><select id="tradeFilterResult"><option value="">All / 전체</option><option value="WIN">Win / 수익</option><option value="LOSS">Loss / 손실</option><option value="BREAKEVEN">Breakeven / 본전</option></select></div>
<button id="tradeFilterReset" type="button">Reset Filters / 필터 초기화</button>
</div>

<div class="grid" style="margin-bottom:10px">
<div class="card"><h2>Filtered Trades / 필터 거래수</h2><div id="tradeDetailCount" class="big">0</div></div>
<div class="card"><h2>Filtered Realized P/L / 필터 실현손익</h2><div id="tradeDetailPnl" class="big">-</div></div>
<div class="card"><h2>Filtered Win Rate / 필터 승률</h2><div id="tradeDetailWinRate" class="big">-</div></div>
<div class="card"><h2>Average Holding Time / 평균 보유시간</h2><div id="tradeDetailHold" class="big">-</div></div>
</div>

<div class="scroll-table">
<table>
<thead><tr>
<th>Entry Time / 진입시간</th>
<th>Exit Time / 청산시간</th>
<th>Holding / 보유시간</th>
<th>Symbol / 종목</th>
<th>Entry Price / 진입가</th>
<th>Exit Price / 청산가</th>
<th>Qty / 수량</th>
<th>Realized P/L / 실현손익</th>
<th>Return / 수익률</th>
<th>Result / 결과</th>
<th>Exit Reason / 청산사유</th>
<th>Order ID / 주문 ID</th>
</tr></thead>
<tbody id="tradeDetailRows"></tbody>
</table>
</div>
<div class="note" id="tradeDetailSource"></div>
</div>
'''

JS = r'''
let v310TradeDetails=[];

function v310Num(v){
  let n=Number(v);
  return Number.isFinite(n)?n:null;
}
function v310Date(v){return String(v||'').slice(0,10);}
function v310HoldingMinutes(row){
  let a=Date.parse(row.entry_time||'');
  let b=Date.parse(row.exit_time||row.time||'');
  if(!Number.isFinite(a)||!Number.isFinite(b)||b<a)return null;
  return (b-a)/60000;
}
function v310HoldingText(minutes){
  if(minutes===null)return '-';
  if(minutes<60)return minutes.toFixed(1)+' min';
  let h=Math.floor(minutes/60),m=Math.round(minutes%60);
  return h+'h '+m+'m';
}
function v310Result(row){
  let p=v310Num(row.pnl);
  if(p===null||p===0)return 'BREAKEVEN';
  return p>0?'WIN':'LOSS';
}
function v310Unique(values){
  return [...new Set(values.filter(x=>x!==null&&x!==undefined&&String(x)!==''))].sort();
}
function v310FillSelect(id,values){
  let e=document.getElementById(id);
  if(!e)return;
  let current=e.value;
  let first=e.options[0].outerHTML;
  e.innerHTML=first+v310Unique(values).map(v=>`<option value="${String(v).replace(/"/g,'&quot;')}">${v}</option>`).join('');
  if([...e.options].some(o=>o.value===current))e.value=current;
}
function v310ApplyFilters(){
  let date=document.getElementById('tradeFilterDate')?.value||'';
  let symbol=document.getElementById('tradeFilterSymbol')?.value||'';
  let reason=document.getElementById('tradeFilterReason')?.value||'';
  let result=document.getElementById('tradeFilterResult')?.value||'';

  let rows=v310TradeDetails.filter(r=>{
    if(date&&v310Date(r.exit_time||r.time)!==date)return false;
    if(symbol&&String(r.symbol||'')!==symbol)return false;
    if(reason&&String(r.reason||'UNKNOWN')!==reason)return false;
    if(result&&v310Result(r)!==result)return false;
    return true;
  });

  let pnls=rows.map(r=>v310Num(r.pnl)).filter(v=>v!==null);
  let total=pnls.reduce((a,b)=>a+b,0);
  let wins=pnls.filter(v=>v>0).length;
  let holds=rows.map(v310HoldingMinutes).filter(v=>v!==null);
  let avgHold=holds.length?holds.reduce((a,b)=>a+b,0)/holds.length:null;

  setv('tradeDetailCount',rows.length);
  setv('tradeDetailPnl',pnls.length?money(total):'-',total>=0?'PASS':'FAIL');
  setv('tradeDetailWinRate',pnls.length?pct(wins/pnls.length):'-');
  setv('tradeDetailHold',v310HoldingText(avgHold));

  let body=document.getElementById('tradeDetailRows');
  if(body){
    body.innerHTML=rows.map(r=>{
      let pnl=v310Num(r.pnl);
      let resultText=v310Result(r);
      let resultLabel=resultText==='WIN'?'WIN / 수익':resultText==='LOSS'?'LOSS / 손실':'BREAKEVEN / 본전';
      let resultClass=resultText==='WIN'?'trade-positive':resultText==='LOSS'?'trade-negative':'trade-flat';
      let ret=v310Num(r.realized_return);
      return `<tr>
        <td>${r.entry_time||'-'}</td>
        <td>${r.exit_time||r.time||'-'}</td>
        <td>${v310HoldingText(v310HoldingMinutes(r))}</td>
        <td>${r.symbol||'-'}</td>
        <td>${r.entry_price===null||r.entry_price===undefined?'-':Number(r.entry_price).toFixed(3)}</td>
        <td>${r.exit_price===null||r.exit_price===undefined?'-':Number(r.exit_price).toFixed(3)}</td>
        <td>${r.qty===null||r.qty===undefined?'-':r.qty}</td>
        <td class="${resultClass}">${pnl===null?'-':money(pnl)}</td>
        <td>${ret===null?'-':pct(ret)}</td>
        <td class="${resultClass}">${resultLabel}</td>
        <td>${r.reason||'UNKNOWN'}</td>
        <td>${r.exit_order_id||r.record_id||'-'}</td>
      </tr>`;
    }).join('')||'<tr><td colspan="12">No matching trades / 조건에 맞는 거래가 없습니다</td></tr>';
  }
}
function v310LoadTradeDetails(d){
  let a=d.trade_analytics||{};
  v310TradeDetails=Array.isArray(a.trade_details)?a.trade_details:[];
  v310FillSelect('tradeFilterDate',v310TradeDetails.map(r=>v310Date(r.exit_time||r.time)));
  v310FillSelect('tradeFilterSymbol',v310TradeDetails.map(r=>r.symbol||'UNKNOWN'));
  v310FillSelect('tradeFilterReason',v310TradeDetails.map(r=>r.reason||'UNKNOWN'));
  let source=document.getElementById('tradeDetailSource');
  if(source){
    source.textContent='Source / 데이터 출처: '+((a.source_ledgers||[]).join(', ')||'No canonical source / 정식 데이터 없음');
  }
  v310ApplyFilters();
}
async function v310Refresh(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let d=await response.json();
    v310LoadTradeDetails(d);
  }catch(error){
    let source=document.getElementById('tradeDetailSource');
    if(source)source.textContent='Trade detail load error / 거래 상세 로드 오류: '+error;
  }
}
function v310Bind(){
  ['tradeFilterDate','tradeFilterSymbol','tradeFilterReason','tradeFilterResult'].forEach(id=>{
    let e=document.getElementById(id);
    if(e)e.addEventListener('change',v310ApplyFilters);
  });
  let reset=document.getElementById('tradeFilterReset');
  if(reset)reset.addEventListener('click',()=>{
    ['tradeFilterDate','tradeFilterSymbol','tradeFilterReason','tradeFilterResult'].forEach(id=>{
      let e=document.getElementById(id);if(e)e.value='';
    });
    v310ApplyFilters();
  });
}
document.addEventListener('DOMContentLoaded',()=>{
  v310Bind();
  v310Refresh();
  setInterval(v310Refresh,30000);
});
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=r"C:\stock-bot")
    args = parser.parse_args()

    target = Path(args.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if 'id="tradeDetailSection"' in text:
        print("V3.10 TRADE DETAIL UI ALREADY PRESENT")
        return 0

    if "</style>" not in text:
        raise RuntimeError("V3.10 STYLE END MARKER NOT FOUND")
    text = text.replace("</style>", CSS + "\n</style>", 1)

    marker = '''<div class="section">
<h3>Recent Timeline / 최근 거래 흐름</h3>
'''
    if marker not in text:
        raise RuntimeError("V3.10 RECENT TIMELINE MARKER NOT FOUND")
    text = text.replace(marker, SECTION + "\n" + marker, 1)

    if "</script>" not in text:
        raise RuntimeError("V3.10 SCRIPT END MARKER NOT FOUND")
    text = text.replace("</script>", JS + "\n</script>", 1)

    text = text.replace(
        "V3.9 Canonical Performance / 정식 성과 데이터",
        "V3.10 Canonical Trade Detail / 정식 거래 상세",
        1,
    )

    target.write_text(text, encoding="utf-8")
    print("V3.10 BILINGUAL TRADE DETAIL UI: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
