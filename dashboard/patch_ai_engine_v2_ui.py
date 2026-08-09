
from pathlib import Path
import argparse

TARGET=Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION='''<div class="section" id="aiEngineV2Section">
<h3>AI Engine V2 Integrated Build / AI 엔진 V2 통합 개발</h3>
<div class="grid">
<div class="card"><h2>Development / 개발</h2><div id="v2Development" class="big"></div></div>
<div class="card"><h2>Real Evidence / 실제 검증 데이터</h2><div id="v2Evidence" class="big"></div></div>
<div class="card"><h2>Lifecycle / 전략 라이프사이클</h2><div id="v2Lifecycle" class="big"></div></div>
<div class="card"><h2>Shadow Challengers / 섀도 챌린저</h2><div id="v2Challengers" class="big"></div></div>
<div class="card"><h2>Live Trading / 실거래</h2><div id="v2Live" class="big"></div></div>
<div class="card"><h2>Auto Promotion / 자동 승격</h2><div id="v2Promotion" class="big"></div></div>
</div>

<div style="margin-top:12px">
<h3>V3.19-V3.30 Development Matrix / 통합 개발 단계</h3>
<div class="scroll-table">
<table>
<thead><tr><th>Version / 버전</th><th>Component / 구성</th><th>Status / 상태</th><th>Meaning / 의미</th></tr></thead>
<tbody id="v2StageRows"></tbody>
</table>
</div>
</div>

<div class="two" style="margin-top:12px">
<div class="card"><h2>Safety Locks / 안전 잠금</h2><div id="v2Safety" class="note"></div></div>
<div class="card"><h2>Current Meaning / 현재 의미</h2><div id="v2Meaning" class="note"></div></div>
</div>

<div class="note">
Software development can complete before Paper evidence / 실제 검증 전에도 소프트웨어 개발 완료 가능 |
Synthetic tests validate software behavior only / 가상 테스트는 소프트웨어 동작만 검증 |
Live remains locked / 실거래 잠금 유지
</div>
</div>'''

JS=r'''function aiV2StageName(v){
  let map={
    'V3.19':'Shadow Challenger / 섀도 챌린저',
    'V3.20':'Champion vs Challenger / 챔피언 비교',
    'V3.21':'Promotion Gate / 승격 게이트',
    'V3.22':'Strategy Registry / 전략 레지스트리',
    'V3.23':'Regime Selector / 시장환경 선택기',
    'V3.24':'Portfolio Intelligence / 포트폴리오 지능',
    'V3.25':'AI Engine V2 Core / AI 엔진 V2 코어',
    'V3.26':'Promotion Manager / 승격 관리자',
    'V3.27':'Rollback Manager / 롤백 관리자',
    'V3.28':'Lifecycle Automation / 라이프사이클 자동화',
    'V3.29':'Safety Supervisor / 안전 감독',
    'V3.30':'Integrated Engine / 통합 엔진'
  };
  return map[v]||v;
}
function aiV2Meaning(status){
  if((status||'').includes('WAITING'))return 'WAITING FOR REAL EVIDENCE / 실제 증거 대기';
  if((status||'').includes('LOCK'))return 'LOCKED / 잠금';
  if((status||'').includes('PASS'))return 'SOFTWARE READY / 소프트웨어 준비';
  return status||'-';
}
function loadAiEngineV2(d){
  let a=((d.trade_analytics||{}).ai_engine_v2)||{};
  let stages=a.stages||{};
  setv('v2Development',a.development_status||'-',a.development_status==='COMPLETE'?'PASS':'WAIT');
  setv('v2Evidence',a.real_evidence_status||'-',a.real_evidence_status==='IN_PROGRESS'?'WAIT':'PASS');
  setv('v2Live',a.live_trading_status||'LOCKED','FAIL');
  setv('v2Promotion',a.automatic_promotion_status||'LOCKED','FAIL');
  setv('v2Lifecycle',(stages['V3.28']||{}).lifecycle_state||'-');
  setv('v2Challengers',(stages['V3.19']||{}).challenger_count??0);

  let versions=['V3.19','V3.20','V3.21','V3.22','V3.23','V3.24','V3.25','V3.26','V3.27','V3.28','V3.29'];
  let rows=versions.map(v=>{
    let s=stages[v]||{};
    return `<tr><td>${v}</td><td>${aiV2StageName(v)}</td><td>${s.status||'-'}</td><td>${aiV2Meaning(s.status)}</td></tr>`;
  });
  rows.push(`<tr><td>V3.30</td><td>${aiV2StageName('V3.30')}</td><td>${a.status||'-'}</td><td>${aiV2Meaning(a.status)}</td></tr>`);
  let table=document.getElementById('v2StageRows');
  if(table)table.innerHTML=rows.join('');

  let locks=((stages['V3.29']||{}).locks)||{};
  setv('v2Safety',
    'Live / 실거래: '+(locks.live_trading_locked?'LOCKED':'UNLOCKED')+
    ' | Broker Write / 브로커 쓰기: '+(locks.broker_write_locked?'LOCKED':'UNLOCKED')+
    ' | Auto Promotion / 자동 승격: '+(locks.automatic_promotion_locked?'LOCKED':'UNLOCKED')+
    ' | Auto Strategy Change / 자동 전략 변경: '+(locks.automatic_strategy_change_locked?'LOCKED':'UNLOCKED')
  );

  setv('v2Meaning',
    a.real_evidence_status==='IN_PROGRESS'
      ? 'Development is complete; real Paper evidence is still accumulating. / 개발은 완료되었고 실제 Paper 증거는 계속 축적 중입니다.'
      : 'Development and current evidence gates are satisfied. / 개발 및 현재 증거 게이트가 충족되었습니다.'
  );
}
async function refreshAiEngineV2(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let data=await response.json();
    loadAiEngineV2(data);
  }catch(error){
    let e=document.getElementById('v2Meaning');
    if(e)e.textContent='AI Engine V2 load error / AI 엔진 V2 로드 오류: '+error;
  }
}
document.addEventListener('DOMContentLoaded',()=>{
  refreshAiEngineV2();
  setInterval(refreshAiEngineV2,30000);
});'''

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'id="aiEngineV2Section"' not in text:
        anchor='<div class="section" id="improvementCandidatesSection">'
        idx=text.find(anchor)
        if idx<0:
            raise RuntimeError("AI ENGINE V2 UI SECTION ANCHOR NOT FOUND")
        text=text[:idx]+SECTION+"\n"+text[idx:]

    if 'function loadAiEngineV2(d)' not in text:
        anchor='function loadImprovementCandidates(d){'
        idx=text.find(anchor)
        if idx<0:
            anchor='</script>'
            idx=text.find(anchor)
            if idx<0:
                raise RuntimeError("AI ENGINE V2 UI SCRIPT ANCHOR NOT FOUND")
        text=text[:idx]+JS+"\n"+text[idx:]

    text=text.replace(
        'V3.18 AI Strategy Improvement Candidates / AI 전략 개선 후보',
        'AI Engine V2 Integrated / AI 엔진 V2 통합',
        1,
    )

    target.write_text(text,encoding="utf-8")
    print("AI ENGINE V2 BILINGUAL UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
