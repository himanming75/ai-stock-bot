
from pathlib import Path
import argparse

TARGET = Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION = '''<div class="section" id="readinessHistorySection">
<h3>Readiness History & Evidence Trend / 준비도 이력 및 증거 추세</h3>
<div class="grid">
<div class="card"><h2>History Records / 이력 기록수</h2><div id="histRecordCount" class="big"></div></div>
<div class="card"><h2>Latest Score / 최신 점수</h2><div id="histLatestScore" class="big"></div><div id="histScoreDelta" class="note"></div></div>
<div class="card"><h2>Latest Trade Count / 최신 거래수</h2><div id="histTradeCount" class="big"></div><div id="histTradeDelta" class="note"></div></div>
<div class="card"><h2>Next Milestone / 다음 마일스톤</h2><div id="histNextMilestone" class="big"></div></div>
<div class="card"><h2>Status Changes / 상태 변경수</h2><div id="histStatusChangeCount" class="big"></div></div>
<div class="card"><h2>History Write / 이력 기록</h2><div id="histWriteState" class="big"></div><div id="histHistoryFile" class="note"></div></div>
</div>
<div class="two" style="margin-top:12px">
<div><h3>Overall Score Trend / 종합점수 추세</h3><div id="histScoreChart" class="chartbox"></div></div>
<div><h3>Evidence Growth / 증거 누적</h3><div id="histTradeChart" class="chartbox"></div></div>
</div>
<div class="two" style="margin-top:12px">
<div><h3>Score Components / 점수 구성 추세</h3><div id="histComponentTable" class="card"></div></div>
<div><h3>Milestones / 마일스톤</h3><div id="histMilestoneTable" class="card"></div></div>
</div>
<div style="margin-top:12px">
<h3>Status Change History / 상태 변경 이력</h3>
<table><thead><tr><th>Time / 시간</th><th>From / 이전</th><th>To / 이후</th><th>Trades / 거래수</th><th>Score / 점수</th></tr></thead><tbody id="histStatusRows"></tbody></table>
</div>
<div class="note">Analytics history only / 분석 이력만 기록 | Broker/Paper runtime unchanged / 브로커·페이퍼 런타임 변경 없음</div>
</div>'''

JS = r'''function histLineChart(points,valueKey,maxY){
  if(!points||points.length<2){
    return '<div class="chart-empty">Need more history points / 이력 포인트가 더 필요합니다</div>';
  }
  let vals=points.map(p=>Number(p[valueKey])).filter(Number.isFinite);
  if(vals.length<2)return '<div class="chart-empty">Insufficient numeric history / 숫자 이력 부족</div>';
  let w=600,h=210,pad=24;
  let min=Math.min(...vals),max=Math.max(...vals);
  if(maxY!==undefined){min=0;max=maxY;}
  if(max===min){max=min+1;}
  let coords=points.map((p,i)=>{
    let v=Number(p[valueKey]);
    if(!Number.isFinite(v))return null;
    let x=pad+(i*(w-2*pad)/Math.max(1,points.length-1));
    let y=h-pad-((v-min)/(max-min))*(h-2*pad);
    return [x,y];
  }).filter(Boolean);
  let poly=coords.map(c=>c.join(',')).join(' ');
  return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
    <line x1="${pad}" y1="${h-pad}" x2="${w-pad}" y2="${h-pad}" stroke="#30363d"/>
    <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${h-pad}" stroke="#30363d"/>
    <polyline fill="none" stroke="#58a6ff" stroke-width="3" points="${poly}"/>
    <text x="${pad}" y="16" fill="#8b949e" font-size="11">${max.toFixed(1)}</text>
    <text x="${pad}" y="${h-4}" fill="#8b949e" font-size="11">${min.toFixed(1)}</text>
  </svg>`;
}
function histStatusLabel(v){
  let map={
    'NOT_READY':'NOT READY / 준비 안됨',
    'EVALUATING':'EVALUATING / 평가 중',
    'CONDITIONAL':'CONDITIONAL / 조건부',
    'READY_FOR_EXTENDED_PAPER':'EXTENDED PAPER READY / 추가 페이퍼 준비'
  };
  return map[v]||v||'-';
}
function loadReadinessHistory(d){
  let h=((d.trade_analytics||{}).readiness_history)||{};
  let latest=h.latest||{};
  let trend=h.trend||[];
  let milestones=h.milestones||{};

  setv('histRecordCount',h.history_record_count??0);
  setv('histLatestScore',latest.overall_score===null||latest.overall_score===undefined?'-':Number(latest.overall_score).toFixed(1)+'/100');
  setv('histScoreDelta',h.score_delta_from_previous===null||h.score_delta_from_previous===undefined?'No previous change / 이전 변화 없음':'Delta / 변화: '+Number(h.score_delta_from_previous).toFixed(1));
  setv('histTradeCount',latest.canonical_numeric_trade_count??0);
  setv('histTradeDelta',h.trade_count_delta_from_previous===null||h.trade_count_delta_from_previous===undefined?'No previous change / 이전 변화 없음':'Delta / 변화: '+h.trade_count_delta_from_previous);
  setv('histNextMilestone',milestones.next_milestone?milestones.next_milestone+' trades / 거래':'All tracked milestones reached / 추적 마일스톤 완료');
  setv('histStatusChangeCount',(h.status_changes||[]).length);
  setv('histWriteState',(h.write_result||{}).written?'WRITTEN / 기록됨':'UNCHANGED / 변화없음',(h.write_result||{}).written?'PASS':'WAIT');
  setv('histHistoryFile',h.history_file||'-');

  document.getElementById('histScoreChart').innerHTML=histLineChart(trend,'overall_score',100);
  let tradePoints=trend.map(x=>({canonical_numeric_trade_count:x.canonical_numeric_trade_count}));
  document.getElementById('histTradeChart').innerHTML=histLineChart(tradePoints,'canonical_numeric_trade_count');

  let scoreKeys=[
    ['sample_confidence','Sample / 표본'],
    ['profitability_quality','Profitability / 수익성'],
    ['risk_quality','Risk / 리스크'],
    ['consistency','Consistency / 일관성'],
    ['diversification','Diversification / 분산']
  ];
  document.getElementById('histComponentTable').innerHTML=scoreKeys.map(([key,label])=>{
    let value=((latest.scores||{})[key]);
    return `<div class="alloc-row"><div class="alloc-label" style="width:150px">${label}</div><div class="alloc-track"><div class="alloc-fill" style="width:${Math.max(0,Math.min(100,Number(value)||0))}%"></div></div><div class="alloc-pct">${Number(value||0).toFixed(1)}</div></div>`;
  }).join('')||'No scores / 점수 없음';

  let reached=milestones.reached||[];
  document.getElementById('histMilestoneTable').innerHTML=[10,20,50,100].map(m=>`<div class="alloc-row"><div class="alloc-label">${m} trades</div><div class="note">${reached.includes(m)?'REACHED / 달성':'WAITING / 대기'}</div></div>`).join('');

  document.getElementById('histStatusRows').innerHTML=(h.status_changes||[]).slice().reverse().map(r=>`<tr><td>${r.recorded_at_utc||'-'}</td><td>${histStatusLabel(r.from_status)}</td><td>${histStatusLabel(r.to_status)}</td><td>${r.canonical_numeric_trade_count??'-'}</td><td>${r.overall_score??'-'}</td></tr>`).join('')
    ||'<tr><td colspan="5">No status changes yet / 아직 상태 변경 없음</td></tr>';
}
async function refreshReadinessHistory(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let data=await response.json();
    loadReadinessHistory(data);
  }catch(error){
    let e=document.getElementById('histHistoryFile');
    if(e)e.textContent='History load error / 이력 로드 오류: '+error;
  }
}
document.addEventListener('DOMContentLoaded',()=>{
  refreshReadinessHistory();
  setInterval(refreshReadinessHistory,30000);
});'''

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()

    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if 'id="readinessHistorySection"' in text:
        print("V3.13 HISTORY UI ALREADY PRESENT")
        return 0

    marker = '<div class="section" id="readinessSection">\n<h3>Strategy Quality & Readiness / 전략 품질 및 준비도</h3>\n'
    if marker not in text:
        raise RuntimeError("V3.13 READINESS INSERT MARKER NOT FOUND")
    text = text.replace(marker, SECTION + "\n" + marker, 1)

    if "</script>" not in text:
        raise RuntimeError("V3.13 SCRIPT END MARKER NOT FOUND")
    text = text.replace("</script>", JS + "\n</script>", 1)

    text = text.replace(
        "V3.12 Strategy Readiness / 전략 준비도",
        "V3.13 Readiness Trend / 준비도 추세",
        1,
    )

    target.write_text(text, encoding="utf-8")
    print("V3.13 BILINGUAL HISTORY UI: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
