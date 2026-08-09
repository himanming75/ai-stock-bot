
from pathlib import Path
import argparse

TARGET=Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION='''<div class="section" id="readinessSection">
<h3>Strategy Quality & Readiness / 전략 품질 및 준비도</h3>
<div class="grid">
<div class="card"><h2>Overall Score / 종합점수</h2><div id="readyOverall" class="big"></div><div id="readyStatus" class="note"></div></div>
<div class="card"><h2>Sample Confidence / 표본 신뢰도</h2><div id="readySample" class="big"></div></div>
<div class="card"><h2>Profitability Quality / 수익성 품질</h2><div id="readyProfit" class="big"></div></div>
<div class="card"><h2>Risk Quality / 리스크 품질</h2><div id="readyRisk" class="big"></div></div>
<div class="card"><h2>Consistency / 일관성</h2><div id="readyConsistency" class="big"></div></div>
<div class="card"><h2>Diversification / 분산도</h2><div id="readyDiversification" class="big"></div></div>
</div>
<div class="two" style="margin-top:12px">
<div class="card"><h2>Readiness Gate / 준비도 게이트</h2><div id="readyGate" class="big"></div><div id="readyThresholds" class="note"></div></div>
<div class="card"><h2>Blockers / 준비도 차단 요인</h2><div id="readyBlockers" class="note"></div></div>
</div>
<div class="card" style="margin-top:12px">
<h2>Interpretation / 해석</h2>
<div id="readyInterpretation" class="note"></div>
<div class="note">Advisory only / 참고용 평가 | No automatic promotion / 자동 승격 없음 | No Live approval / 실거래 승인 아님</div>
</div>
</div>'''

JS=r'''function readyScore(v){
  let n=Number(v); return Number.isFinite(n)?n.toFixed(1)+'/100':'-';
}
function readyStatusLabel(status){
  let map={
    'NOT_READY':'NOT READY / 준비 안됨',
    'EVALUATING':'EVALUATING / 평가 중',
    'CONDITIONAL':'CONDITIONAL / 조건부',
    'READY_FOR_EXTENDED_PAPER':'READY FOR EXTENDED PAPER / 추가 페이퍼 검증 준비'
  };
  return map[status]||status||'-';
}
function readyClass(status){
  if(status==='READY_FOR_EXTENDED_PAPER')return 'PASS';
  if(status==='EVALUATING'||status==='CONDITIONAL')return 'WAIT';
  return 'FAIL';
}
function loadReadiness(d){
  let r=((d.trade_analytics||{}).strategy_readiness)||{};
  let s=r.scores||{}, t=r.thresholds||{};
  setv('readyOverall',readyScore(r.overall_score),readyClass(r.status));
  setv('readyStatus',readyStatusLabel(r.status));
  setv('readySample',readyScore(s.sample_confidence),s.sample_confidence>=80?'PASS':'WAIT');
  setv('readyProfit',readyScore(s.profitability_quality),s.profitability_quality>=65?'PASS':'WAIT');
  setv('readyRisk',readyScore(s.risk_quality),s.risk_quality>=65?'PASS':'WAIT');
  setv('readyConsistency',readyScore(s.consistency),s.consistency>=65?'PASS':'WAIT');
  setv('readyDiversification',readyScore(s.diversification),s.diversification>=65?'PASS':'WAIT');
  setv('readyGate',readyStatusLabel(r.status),readyClass(r.status));
  setv('readyThresholds','Canonical trades / 정식 거래: '+(r.canonical_numeric_trade_count??0)+' | Evaluation / 평가: '+(t.minimum_evaluation_trades??10)+' | Ready sample / 준비 표본: '+(t.minimum_ready_trades??20));
  let blockers=r.blockers||[];
  document.getElementById('readyBlockers').innerHTML=blockers.length?blockers.map(x=>'<div>- '+x+'</div>').join(''):'No blockers / 차단 요인 없음';
  setv('readyInterpretation',r.interpretation||'-');
}
async function refreshReadiness(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let data=await response.json(); loadReadiness(data);
  }catch(error){
    let e=document.getElementById('readyInterpretation');
    if(e)e.textContent='Readiness load error / 준비도 로드 오류: '+error;
  }
}
document.addEventListener('DOMContentLoaded',()=>{refreshReadiness();setInterval(refreshReadiness,30000);});'''

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'id="readinessSection"' in text:
        print("V3.12 READINESS UI ALREADY PRESENT")
        return 0

    marker='<div class="section" id="diagnosticsSection">\n<h3>Canonical Performance Diagnostics / 정식 거래 성과 진단</h3>\n'
    if marker not in text:
        raise RuntimeError("V3.12 DIAGNOSTICS INSERT MARKER NOT FOUND")
    text=text.replace(marker,SECTION+"\n"+marker,1)

    if "</script>" not in text:
        raise RuntimeError("V3.12 SCRIPT END MARKER NOT FOUND")
    text=text.replace("</script>",JS+"\n</script>",1)

    text=text.replace(
        "V3.11 Performance Diagnostics / 거래 성과 진단",
        "V3.12 Strategy Readiness / 전략 준비도",
        1,
    )

    target.write_text(text,encoding="utf-8")
    print("V3.12 BILINGUAL READINESS UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
