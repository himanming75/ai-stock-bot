
from pathlib import Path
import argparse

TARGET = Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION = '''<div class="section" id="stressTestSection">
<h3>Strategy Stress Test / 전략 스트레스 테스트</h3>
<div class="grid">
<div class="card"><h2>Stress Status / 스트레스 상태</h2><div id="stressStatus" class="big"></div><div id="stressSample" class="note"></div></div>
<div class="card"><h2>Canonical Trades / 정식 거래수</h2><div id="stressTradeCount" class="big"></div></div>
<div class="card"><h2>Scenarios / 시나리오</h2><div id="stressScenarioCount" class="big"></div></div>
<div class="card"><h2>Severe Degradation / 심각 스트레스 악화율</h2><div id="stressSevereDegradation" class="big"></div></div>
</div>

<div style="margin-top:12px">
<h3>Scenario Comparison / 시나리오 비교</h3>
<div class="scroll-table">
<table>
<thead><tr>
<th>Scenario / 시나리오</th>
<th>Friction / 거래마찰</th>
<th>Winner Haircut / 수익축소</th>
<th>Loss Amplification / 손실확대</th>
<th>Net P/L / 순손익</th>
<th>Win Rate / 승률</th>
<th>Profit Factor / 수익팩터</th>
<th>Max Drawdown / 최대낙폭</th>
<th>Avg Trade / 평균거래</th>
<th>Readiness / 준비도</th>
<th>Score / 점수</th>
<th>Sample / 표본</th>
</tr></thead>
<tbody id="stressScenarioRows"></tbody>
</table>
</div>
</div>

<div class="two" style="margin-top:12px">
<div><h3>Net P/L by Scenario / 시나리오별 순손익</h3><div id="stressPnlChart" class="card"></div></div>
<div><h3>Readiness Score by Scenario / 시나리오별 준비도 점수</h3><div id="stressReadinessChart" class="card"></div></div>
</div>

<div class="card" style="margin-top:12px">
<h2>Interpretation / 해석</h2>
<div id="stressInterpretation" class="note"></div>
<div class="note">Simulation only / 시뮬레이션 전용 | Canonical records unchanged / 정식 거래 기록 변경 없음 | No Live approval / 실거래 승인 아님</div>
</div>
</div>'''

JS = r'''function stressScenarioLabel(id){
  let map={
    'BASELINE':'Baseline / 기준',
    'MILD':'Mild / 약한 스트레스',
    'MODERATE':'Moderate / 중간 스트레스',
    'SEVERE':'Severe / 강한 스트레스'
  };
  return map[id]||id||'-';
}
function stressReadyLabel(status){
  let map={
    'NOT_READY':'NOT READY / 준비 안됨',
    'EVALUATING':'EVALUATING / 평가 중',
    'CONDITIONAL':'CONDITIONAL / 조건부',
    'READY_FOR_EXTENDED_PAPER':'EXTENDED PAPER READY / 추가 페이퍼 준비'
  };
  return map[status]||status||'-';
}
function stressPF(v){
  if(v==='INF')return 'INF';
  let n=Number(v);
  return Number.isFinite(n)?n.toFixed(2):'-';
}
function stressBarRows(scenarios,labelFn){
  let values=(scenarios||[]).map(s=>({
    name:stressScenarioLabel((s.scenario||{}).id),
    value:labelFn(s)
  }));
  let numeric=values.map(x=>Number(x.value)).filter(Number.isFinite);
  let max=numeric.length?Math.max(...numeric.map(Math.abs),1):1;
  return values.map(x=>{
    let n=Number(x.value);
    let width=Number.isFinite(n)?Math.min(100,Math.abs(n)/max*100):0;
    return `<div class="alloc-row">
      <div class="alloc-label" style="width:145px">${x.name}</div>
      <div class="alloc-track"><div class="alloc-fill" style="width:${width}%"></div></div>
      <div class="alloc-pct" style="width:80px">${Number.isFinite(n)?n.toFixed(2):'-'}</div>
    </div>`;
  }).join('');
}
function loadStressTest(d){
  let st=((d.trade_analytics||{}).strategy_stress_test)||{};
  let scenarios=st.scenarios||[];

  setv('stressStatus',st.status||'-',st.sample_status==='PASS_SAMPLE'?'PASS':'WAIT');
  setv('stressSample',(st.sample_status||'-')+' | minimum / 최소 '+(st.minimum_interpretation_sample??10));
  setv('stressTradeCount',st.canonical_numeric_trade_count??0);
  setv('stressScenarioCount',st.scenario_count??0);

  let deg=Number(st.severe_degradation_pct);
  setv('stressSevereDegradation',Number.isFinite(deg)?pct(deg):'-',Number.isFinite(deg)&&deg>1?'FAIL':'WAIT');

  document.getElementById('stressScenarioRows').innerHTML=
    scenarios.map(s=>{
      let sc=s.scenario||{}, stats=s.stats||{}, ready=s.readiness||{};
      return `<tr>
        <td>${stressScenarioLabel(sc.id)}</td>
        <td>${sc.friction_bps_per_leg??0} bps/leg</td>
        <td>${sc.winner_haircut_pct??0}%</td>
        <td>${sc.loser_amplification_pct??0}%</td>
        <td>${stats.net_realized_pnl===null||stats.net_realized_pnl===undefined?'-':money(stats.net_realized_pnl)}</td>
        <td>${stats.win_rate===null||stats.win_rate===undefined?'-':pct(stats.win_rate)}</td>
        <td>${stressPF(stats.profit_factor)}</td>
        <td>${stats.max_realized_drawdown===null||stats.max_realized_drawdown===undefined?'-':money(stats.max_realized_drawdown)}</td>
        <td>${stats.average_trade===null||stats.average_trade===undefined?'-':money(stats.average_trade)}</td>
        <td>${stressReadyLabel(ready.status)}</td>
        <td>${ready.overall_score===null||ready.overall_score===undefined?'-':Number(ready.overall_score).toFixed(1)}</td>
        <td>${s.sample_status==='PASS_SAMPLE'?'PASS / 충분':'INSUFFICIENT / 부족'}</td>
      </tr>`;
    }).join('')
    ||'<tr><td colspan="12">No stress data / 스트레스 데이터 없음</td></tr>';

  document.getElementById('stressPnlChart').innerHTML=
    stressBarRows(scenarios,s=>(s.stats||{}).net_realized_pnl)
    ||'No data / 데이터 없음';

  document.getElementById('stressReadinessChart').innerHTML=
    stressBarRows(scenarios,s=>(s.readiness||{}).overall_score)
    ||'No data / 데이터 없음';

  setv('stressInterpretation',st.interpretation||'-');
}
async function refreshStressTest(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let data=await response.json();
    loadStressTest(data);
  }catch(error){
    let e=document.getElementById('stressInterpretation');
    if(e)e.textContent='Stress test load error / 스트레스 테스트 로드 오류: '+error;
  }
}
document.addEventListener('DOMContentLoaded',()=>{
  refreshStressTest();
  setInterval(refreshStressTest,30000);
});'''

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()

    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if 'id="stressTestSection"' in text:
        print("V3.14 STRESS UI ALREADY PRESENT")
        return 0

    marker = '<div class="section" id="readinessHistorySection">\n<h3>Readiness History & Evidence Trend / 준비도 이력 및 증거 추세</h3>\n'
    if marker not in text:
        raise RuntimeError("V3.14 HISTORY INSERT MARKER NOT FOUND")

    text = text.replace(marker, SECTION + "\n" + marker, 1)

    if "</script>" not in text:
        raise RuntimeError("V3.14 SCRIPT END MARKER NOT FOUND")

    text = text.replace("</script>", JS + "\n</script>", 1)

    text = text.replace(
        "V3.13 Readiness Trend / 준비도 추세",
        "V3.14 Strategy Stress Test / 전략 스트레스 테스트",
        1,
    )

    target.write_text(text, encoding="utf-8")
    print("V3.14 BILINGUAL STRESS TEST UI: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
