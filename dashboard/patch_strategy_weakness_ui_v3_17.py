
from pathlib import Path
import argparse

TARGET = Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION = '''<div class="section" id="weaknessMapSection">
<h3>Strategy Weakness Map / 전략 약점 지도</h3>

<div class="grid">
<div class="card"><h2>Overall Severity / 전체 심각도</h2><div id="weakOverallSeverity" class="big"></div></div>
<div class="card"><h2>Priority Score / 우선순위 점수</h2><div id="weakPriorityScore" class="big"></div></div>
<div class="card"><h2>Total Issues / 총 약점 항목</h2><div id="weakIssueCount" class="big"></div></div>
<div class="card"><h2>Evidence Gaps / 증거 부족</h2><div id="weakEvidenceCount" class="big"></div></div>
<div class="card"><h2>Performance Risks / 성과 위험</h2><div id="weakPerformanceCount" class="big"></div></div>
<div class="card"><h2>Critical + High / 중요 약점</h2><div id="weakCriticalHigh" class="big"></div></div>
</div>

<div style="margin-top:12px">
<h3>Top Priorities / 최우선 약점</h3>
<div id="weakTopCards" class="grid"></div>
</div>

<div style="margin-top:12px">
<h3>Weakness Matrix / 약점 매트릭스</h3>
<div class="scroll-table">
<table>
<thead><tr>
<th>Severity / 심각도</th>
<th>Type / 유형</th>
<th>Category / 분류</th>
<th>Weakness / 약점</th>
<th>Evidence / 근거</th>
<th>Meaning / 의미</th>
<th>Next Evidence / 다음 필요 증거</th>
</tr></thead>
<tbody id="weakIssueRows"></tbody>
</table>
</div>
</div>

<div class="two" style="margin-top:12px">
<div class="card">
<h2>Severity Distribution / 심각도 분포</h2>
<div id="weakSeverityBars"></div>
</div>
<div class="card">
<h2>Interpretation / 해석</h2>
<div id="weakInterpretation" class="note"></div>
</div>
</div>

<div class="note">
Evidence gap does not mean strategy failure / 증거 부족은 전략 실패를 의미하지 않음 |
Diagnostic only / 진단 전용 |
No automatic strategy changes / 자동 전략 변경 없음 |
No Live approval / 실거래 승인 아님
</div>
</div>'''

JS = r'''function weakSeverityClass(severity){
  if(severity==='CRITICAL')return 'FAIL';
  if(severity==='HIGH')return 'FAIL';
  if(severity==='MEDIUM')return 'WAIT';
  if(severity==='LOW')return 'WAIT';
  return 'PASS';
}
function weakTypeLabel(type){
  let map={
    'EVIDENCE_GAP':'EVIDENCE GAP / 증거 부족',
    'PERFORMANCE_RISK':'PERFORMANCE RISK / 성과 위험'
  };
  return map[type]||type||'-';
}
function weakCategoryLabel(category){
  let map={
    'SAMPLE':'Sample / 표본',
    'DOWNSIDE':'Downside / 하방위험',
    'DIVERSIFICATION':'Diversification / 분산',
    'PROFITABILITY':'Profitability / 수익성',
    'RISK':'Risk / 리스크',
    'STRESS':'Stress / 스트레스',
    'ROBUSTNESS':'Robustness / 견고성',
    'REGIME':'Regime / 시장환경',
    'READINESS':'Readiness / 준비도'
  };
  return map[category]||category||'-';
}
function weakJson(value){
  try{return JSON.stringify(value);}catch(e){return '-';}
}
function weakSeverityBar(label,value,max){
  let width=max>0?(value/max*100):0;
  return `<div class="alloc-row">
    <div class="alloc-label" style="width:95px">${label}</div>
    <div class="alloc-track"><div class="alloc-fill" style="width:${width}%"></div></div>
    <div class="alloc-pct">${value}</div>
  </div>`;
}
function loadWeaknessMap(d){
  let w=((d.trade_analytics||{}).strategy_weakness_map)||{};
  let counts=w.severity_counts||{};
  let types=w.type_counts||{};

  setv('weakOverallSeverity',w.overall_severity||'-',weakSeverityClass(w.overall_severity));
  setv('weakPriorityScore',Number.isFinite(Number(w.priority_score))?Number(w.priority_score).toFixed(1)+'/100':'-');
  setv('weakIssueCount',w.issue_count??0);
  setv('weakEvidenceCount',types.EVIDENCE_GAP??0);
  setv('weakPerformanceCount',types.PERFORMANCE_RISK??0);
  setv('weakCriticalHigh',(counts.CRITICAL??0)+(counts.HIGH??0));

  let top=w.top_priorities||[];
  document.getElementById('weakTopCards').innerHTML=
    top.map(x=>`<div class="card">
      <h2>${x.severity} - ${weakCategoryLabel(x.category)}</h2>
      <div class="big ${weakSeverityClass(x.severity)}">${x.title||'-'}</div>
      <div class="note">${weakTypeLabel(x.weakness_type)}</div>
      <div class="note">${x.meaning||'-'}</div>
    </div>`).join('')
    ||'<div class="card">No material weakness detected / 감지된 주요 약점 없음</div>';

  document.getElementById('weakIssueRows').innerHTML=
    (w.issues||[]).map(x=>`<tr>
      <td>${x.severity||'-'}</td>
      <td>${weakTypeLabel(x.weakness_type)}</td>
      <td>${weakCategoryLabel(x.category)}</td>
      <td>${x.title||'-'}</td>
      <td>${weakJson(x.evidence)}</td>
      <td>${x.meaning||'-'}</td>
      <td>${x.next_evidence_needed||'-'}</td>
    </tr>`).join('')
    ||'<tr><td colspan="7">No material weakness detected / 감지된 주요 약점 없음</td></tr>';

  let max=Math.max(
    counts.CRITICAL??0,
    counts.HIGH??0,
    counts.MEDIUM??0,
    counts.LOW??0,
    1
  );
  document.getElementById('weakSeverityBars').innerHTML=
    weakSeverityBar('CRITICAL',counts.CRITICAL??0,max)+
    weakSeverityBar('HIGH',counts.HIGH??0,max)+
    weakSeverityBar('MEDIUM',counts.MEDIUM??0,max)+
    weakSeverityBar('LOW',counts.LOW??0,max);

  setv('weakInterpretation',w.interpretation||'-');
}
async function refreshWeaknessMap(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let data=await response.json();
    loadWeaknessMap(data);
  }catch(error){
    let e=document.getElementById('weakInterpretation');
    if(e)e.textContent='Weakness map load error / 약점 지도 로드 오류: '+error;
  }
}
document.addEventListener('DOMContentLoaded',()=>{
  refreshWeaknessMap();
  setInterval(refreshWeaknessMap,30000);
});'''


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()

    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if 'id="weaknessMapSection"' in text:
        print("V3.17 WEAKNESS UI ALREADY PRESENT")
        return 0

    marker = (
        '<div class="section" id="regimeSection">\n'
        '<h3>Market Regime Performance Analysis / 시장 환경별 전략 성과 분석</h3>\n'
    )

    if marker not in text:
        raise RuntimeError("V3.17 REGIME INSERT MARKER NOT FOUND")

    text = text.replace(marker, SECTION + "\n" + marker, 1)

    if "</script>" not in text:
        raise RuntimeError("V3.17 SCRIPT END MARKER NOT FOUND")

    text = text.replace("</script>", JS + "\n</script>", 1)

    text = text.replace(
        "V3.16 Market Regime Analysis / 시장 환경 분석",
        "V3.17 Strategy Weakness Map / 전략 약점 지도",
        1,
    )

    target.write_text(text, encoding="utf-8")
    print("V3.17 BILINGUAL WEAKNESS UI: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
