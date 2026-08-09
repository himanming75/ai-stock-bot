
from pathlib import Path
import argparse

TARGET=Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION='''<div class="section" id="improvementCandidatesSection">
<h3>AI Strategy Improvement Candidates / AI 전략 개선 후보</h3>
<div class="grid">
<div class="card"><h2>Mode / 모드</h2><div id="impMode" class="big"></div></div>
<div class="card"><h2>Total Candidates / 전체 후보</h2><div id="impCount" class="big"></div></div>
<div class="card"><h2>Evidence Candidates / 증거 수집 후보</h2><div id="impEvidence" class="big"></div></div>
<div class="card"><h2>Strategy Candidates / 전략 변경 후보</h2><div id="impStrategy" class="big"></div></div>
</div>

<div style="margin-top:12px">
<h3>Top Candidates / 우선 개선 후보</h3>
<div class="scroll-table">
<table>
<thead><tr>
<th>Priority / 우선순위</th>
<th>Proposal / 제안</th>
<th>Target / 대상</th>
<th>Source Weakness / 원인 약점</th>
<th>Expected Effect / 예상 효과</th>
<th>Required Validation / 필요 검증</th>
<th>Executable / 실행 가능</th>
</tr></thead>
<tbody id="impRows"></tbody>
</table>
</div>
</div>

<div class="note">
Proposal only / 제안 전용 |
Auto Apply OFF / 자동 적용 없음 |
Paper parameter change OFF / Paper 파라미터 변경 없음 |
Live change OFF / 실거래 변경 없음
</div>
</div>'''

JS=r'''function loadImprovementCandidates(d){
  let x=((d.trade_analytics||{}).strategy_improvement_candidates)||{};

  setv('impMode',x.mode||'-');
  setv('impCount',x.candidate_count??0);
  setv('impEvidence',x.evidence_collection_candidate_count??0);
  setv('impStrategy',x.strategy_change_candidate_count??0);

  let rows=(x.top_candidates||[]).map(c=>`<tr>
    <td>${c.priority_score??'-'}</td>
    <td>${c.proposal_type||'-'}</td>
    <td>${c.change_target||'-'}</td>
    <td>${c.source_weakness_code||'-'}<div class="note">${c.weakness_type||'-'} / ${c.source_severity||'-'}</div></td>
    <td>${c.expected_effect||'-'}</td>
    <td>${c.required_validation||'-'}</td>
    <td>${c.execution_eligible?'YES':'NO'}</td>
  </tr>`).join('');

  let table=document.getElementById('impRows');
  if(table){
    table.innerHTML=rows||'<tr><td colspan="7">No candidates / 후보 없음</td></tr>';
  }
}

async function refreshImprovementCandidates(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let data=await response.json();
    loadImprovementCandidates(data);
  }catch(error){
    let table=document.getElementById('impRows');
    if(table){
      table.innerHTML='<tr><td colspan="7">Improvement candidate load error / 개선 후보 로드 오류</td></tr>';
    }
  }
}

document.addEventListener('DOMContentLoaded',()=>{
  refreshImprovementCandidates();
  setInterval(refreshImprovementCandidates,30000);
});'''


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'id="improvementCandidatesSection"' not in text:
        anchor='<div class="section" id="weaknessMapSection">'
        idx=text.find(anchor)
        if idx < 0:
            raise RuntimeError("V3.18.1 UI SECTION ANCHOR NOT FOUND")
        text=text[:idx]+SECTION+"\n"+text[idx:]

    if 'function loadImprovementCandidates(d)' not in text:
        anchor='function weakSeverityClass(severity){'
        idx=text.find(anchor)
        if idx < 0:
            anchor='</script>'
            idx=text.find(anchor)
            if idx < 0:
                raise RuntimeError("V3.18.1 SCRIPT ANCHOR NOT FOUND")
        text=text[:idx]+JS+"\n"+text[idx:]

    text=text.replace(
        'V3.17 Strategy Weakness Map / 전략 약점 지도',
        'V3.18 AI Strategy Improvement Candidates / AI 전략 개선 후보',
        1,
    )

    target.write_text(text,encoding="utf-8")
    print("V3.18.1 UI INTEGRATION REPAIR: PASS")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
