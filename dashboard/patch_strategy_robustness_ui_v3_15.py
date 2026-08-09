
from pathlib import Path
import argparse

TARGET = Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION = '''<div class="section" id="robustnessSection">
<h3>Strategy Robustness & Failure Boundary / 전략 견고성 및 실패 경계</h3>
<div class="grid">
<div class="card"><h2>Robustness Score / 견고성 점수</h2><div id="robustScore" class="big"></div><div id="robustSample" class="note"></div></div>
<div class="card"><h2>Break-even Friction / 손익분기 거래마찰</h2><div id="robustFriction" class="big"></div><div class="note">bps per leg / 편도 기준</div></div>
<div class="card"><h2>Winner Haircut Boundary / 수익축소 실패경계</h2><div id="robustHaircut" class="big"></div></div>
<div class="card"><h2>Loss Amplification Boundary / 손실확대 실패경계</h2><div id="robustLossAmp" class="big"></div></div>
<div class="card"><h2>PF=1 Friction Boundary / 수익팩터 1 경계</h2><div id="robustPFBoundary" class="big"></div></div>
<div class="card"><h2>Readiness Failure Boundary / 준비도 실패경계</h2><div id="robustReadyBoundary" class="big"></div></div>
</div>

<div class="two" style="margin-top:12px">
<div class="card"><h2>Boundary Observability / 경계 관측 가능성</h2><div id="robustObservability" class="note"></div></div>
<div class="card"><h2>Interpretation / 해석</h2><div id="robustInterpretation" class="note"></div></div>
</div>

<div style="margin-top:12px">
<h3>Failure Boundary Matrix / 실패 경계 매트릭스</h3>
<table>
<thead><tr><th>Boundary / 경계</th><th>Status / 상태</th><th>Value / 값</th><th>Meaning / 의미</th></tr></thead>
<tbody id="robustBoundaryRows"></tbody>
</table>
</div>

<div class="note">Simulation only / 시뮬레이션 전용 | Insufficient sample is capped / 표본 부족 시 점수 제한 | No automatic promotion / 자동 승격 없음 | No Live approval / 실거래 승인 아님</div>
</div>'''

JS = r'''function robustStatusLabel(status){
  let map={
    'FOUND':'FOUND / 발견',
    'UNOBSERVED_NO_LOSING_TRADES':'UNOBSERVED / 관측 손실 없음',
    'NO_WINNERS_OBSERVED':'UNOBSERVED / 관측 수익 없음',
    'FAILED_AT_BASELINE':'FAILED BASELINE / 기준부터 실패',
    'NOT_REACHED_WITHIN_SEARCH_RANGE':'NOT REACHED / 탐색범위 내 미도달',
    'INSUFFICIENT_SAMPLE_BASELINE_NOT_READY':'INSUFFICIENT SAMPLE / 표본 부족',
    'BASELINE_ALREADY_NOT_READY':'BASELINE NOT READY / 기준 준비 안됨'
  };
  return map[status]||status||'-';
}
function robustBoundaryValue(obj,key,suffix){
  if(!obj)return '-';
  let n=Number(obj[key]);
  return Number.isFinite(n)?n.toFixed(2)+(suffix||''):'-';
}
function loadRobustness(d){
  let r=((d.trade_analytics||{}).strategy_robustness)||{};
  let b=r.failure_boundaries||{};
  let friction=b.break_even_friction_bps_per_leg||{};
  let haircut=b.winner_haircut_pct||{};
  let lossamp=b.loss_amplification_pct||{};
  let pf=b.profit_factor_one_friction_bps_per_leg||{};
  let ready=b.readiness_failure_friction_bps_per_leg||{};

  setv('robustScore',Number.isFinite(Number(r.robustness_score))?Number(r.robustness_score).toFixed(1)+'/100':'-',r.sample_status==='PASS_SAMPLE'?'PASS':'WAIT');
  setv('robustSample',(r.sample_status||'-')+' | canonical trades / 정식 거래: '+(r.canonical_numeric_trade_count??0)+' / '+(r.minimum_interpretation_sample??10));
  setv('robustFriction',friction.status==='FOUND'?robustBoundaryValue(friction,'boundary',' bps'):robustStatusLabel(friction.status));
  setv('robustHaircut',haircut.status==='FOUND'?robustBoundaryValue(haircut,'boundary','%'):robustStatusLabel(haircut.status));
  setv('robustLossAmp',lossamp.status==='FOUND'?robustBoundaryValue(lossamp,'boundary','%'):robustStatusLabel(lossamp.status));
  setv('robustPFBoundary',pf.status==='FOUND'?robustBoundaryValue(pf,'boundary_bps_per_leg',' bps'):robustStatusLabel(pf.status));
  setv('robustReadyBoundary',ready.status==='FOUND'?robustBoundaryValue(ready,'boundary_bps_per_leg',' bps'):robustStatusLabel(ready.status));

  let obs=r.observability||{};
  setv('robustObservability','Winners / 수익거래: '+(obs.has_winners?'YES / 있음':'NO / 없음')+' | Losses / 손실거래: '+(obs.has_losses?'YES / 있음':'NO / 없음'));
  setv('robustInterpretation',r.interpretation||'-');

  let rows=[
    ['Break-even friction / 손익분기 마찰',friction,friction.status==='FOUND'?robustBoundaryValue(friction,'boundary',' bps'):'-','Net P/L becomes zero or negative / 순손익이 0 이하가 되는 거래마찰'],
    ['Winner haircut / 수익축소',haircut,haircut.status==='FOUND'?robustBoundaryValue(haircut,'boundary','%'):'-','Winner reduction where Net P/L fails / 수익 축소로 순손익이 실패하는 지점'],
    ['Loss amplification / 손실확대',lossamp,lossamp.status==='FOUND'?robustBoundaryValue(lossamp,'boundary','%'):'-','Loss increase where Net P/L fails / 손실 확대에 따른 실패 지점'],
    ['Profit Factor = 1 / 수익팩터 1',pf,pf.status==='FOUND'?robustBoundaryValue(pf,'boundary_bps_per_leg',' bps'):'-','Friction where PF falls to 1 or below / PF가 1 이하가 되는 마찰'],
    ['Readiness failure / 준비도 실패',ready,ready.status==='FOUND'?robustBoundaryValue(ready,'boundary_bps_per_leg',' bps'):'-','Friction where readiness degrades / 준비도 판정이 악화되는 마찰']
  ];
  document.getElementById('robustBoundaryRows').innerHTML=rows.map(row=>`<tr><td>${row[0]}</td><td>${robustStatusLabel((row[1]||{}).status)}</td><td>${row[2]}</td><td>${row[3]}</td></tr>`).join('');
}
async function refreshRobustness(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let data=await response.json();
    loadRobustness(data);
  }catch(error){
    let e=document.getElementById('robustInterpretation');
    if(e)e.textContent='Robustness load error / 견고성 로드 오류: '+error;
  }
}
document.addEventListener('DOMContentLoaded',()=>{refreshRobustness();setInterval(refreshRobustness,30000);});'''

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=r"C:\stock-bot")
    a = p.parse_args()

    target = Path(a.root) / TARGET
    text = target.read_text(encoding="utf-8")

    if 'id="robustnessSection"' in text:
        print("V3.15 ROBUSTNESS UI ALREADY PRESENT")
        return 0

    marker = '<div class="section" id="stressTestSection">\n<h3>Strategy Stress Test / 전략 스트레스 테스트</h3>\n'
    if marker not in text:
        raise RuntimeError("V3.15 STRESS INSERT MARKER NOT FOUND")

    text = text.replace(marker, SECTION + "\n" + marker, 1)

    if "</script>" not in text:
        raise RuntimeError("V3.15 SCRIPT END MARKER NOT FOUND")

    text = text.replace("</script>", JS + "\n</script>", 1)

    text = text.replace(
        "V3.14 Strategy Stress Test / 전략 스트레스 테스트",
        "V3.15 Robustness Boundaries / 견고성 실패 경계",
        1,
    )

    target.write_text(text, encoding="utf-8")
    print("V3.15 BILINGUAL ROBUSTNESS UI: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
