
from pathlib import Path
import argparse

TARGET = Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION = '''<div class="section" id="regimeSection">
<h3>Market Regime Performance Analysis / 시장 환경별 전략 성과 분석</h3>
<div class="grid">
<div class="card"><h2>Regime Status / 시장환경 상태</h2><div id="regimeStatus" class="big"></div><div id="regimeSample" class="note"></div></div>
<div class="card"><h2>Direction Coverage / 방향환경 관측범위</h2><div id="regimeDirectionCoverage" class="big"></div></div>
<div class="card"><h2>Volatility Coverage / 변동성 관측범위</h2><div id="regimeVolCoverage" class="big"></div></div>
<div class="card"><h2>Evidence Trades / 환경 증거 거래</h2><div id="regimeEvidenceTrades" class="big"></div></div>
<div class="card"><h2>Best Observed Regime / 관측상 최우수 환경</h2><div id="regimeBest" class="big"></div></div>
<div class="card"><h2>Weakest Observed Regime / 관측상 취약 환경</h2><div id="regimeWeakest" class="big"></div></div>
</div>

<div style="margin-top:12px">
<h3>Directional Regime Matrix / 방향 시장환경 성과표</h3>
<div class="scroll-table"><table>
<thead><tr><th>Regime / 환경</th><th>Trades / 거래수</th><th>Net P/L / 순손익</th><th>Win Rate / 승률</th><th>Profit Factor / 수익팩터</th><th>Average P/L / 평균손익</th><th>Max Drawdown / 최대낙폭</th><th>Sample / 표본</th></tr></thead>
<tbody id="regimeDirectionRows"></tbody>
</table></div>
</div>

<div style="margin-top:12px">
<h3>Volatility Regime Matrix / 변동성 환경 성과표</h3>
<div class="scroll-table"><table>
<thead><tr><th>Regime / 환경</th><th>Trades / 거래수</th><th>Net P/L / 순손익</th><th>Win Rate / 승률</th><th>Profit Factor / 수익팩터</th><th>Average P/L / 평균손익</th><th>Max Drawdown / 최대낙폭</th><th>Sample / 표본</th></tr></thead>
<tbody id="regimeVolRows"></tbody>
</table></div>
</div>

<div class="two" style="margin-top:12px">
<div class="card"><h2>Evidence Sources / 환경 증거 출처</h2><div id="regimeSources" class="note"></div></div>
<div class="card"><h2>Interpretation / 해석</h2><div id="regimeInterpretation" class="note"></div></div>
</div>

<div class="note">Explicit evidence only / 명시적 증거만 사용 | No price-based regime guessing / 가격 기반 환경 추측 없음 | UNOBSERVED remains unobserved / 미관측 환경은 그대로 유지 | No Live approval / 실거래 승인 아님</div>
</div>'''

JS = r'''function regimeLabel(name){
  let map={'BULL':'BULL / 상승장','BEAR':'BEAR / 하락장','SIDEWAYS':'SIDEWAYS / 횡보장','HIGH_VOL':'HIGH VOL / 고변동성','NORMAL_VOL':'NORMAL VOL / 보통 변동성','LOW_VOL':'LOW VOL / 저변동성'};
  return map[name]||name||'-';
}
function regimePF(v){
  if(v==='INF')return 'INF';
  let n=Number(v);
  return Number.isFinite(n)?n.toFixed(2):'-';
}
function regimeSample(v){
  let map={'PASS_SAMPLE':'PASS / 충분','INSUFFICIENT_SAMPLE':'INSUFFICIENT / 부족','UNOBSERVED':'UNOBSERVED / 미관측'};
  return map[v]||v||'-';
}
function regimeRow(row){
  return `<tr><td>${regimeLabel(row.name)}</td><td>${row.numeric_trade_count??0}</td><td>${row.net_realized_pnl===null||row.net_realized_pnl===undefined?'-':money(row.net_realized_pnl)}</td><td>${row.win_rate===null||row.win_rate===undefined?'-':pct(row.win_rate)}</td><td>${regimePF(row.profit_factor)}</td><td>${row.average_trade===null||row.average_trade===undefined?'-':money(row.average_trade)}</td><td>${row.max_realized_drawdown===null||row.max_realized_drawdown===undefined?'-':money(row.max_realized_drawdown)}</td><td>${regimeSample(row.sample_status)}</td></tr>`;
}
function loadRegime(d){
  let r=((d.trade_analytics||{}).market_regime_analysis)||{};
  let c=r.coverage||{};
  setv('regimeStatus',r.status||'-',r.status==='PASS_EXPLICIT_REGIME_EVIDENCE_FOUND'?'PASS':'WAIT');
  setv('regimeSample',(r.sample_status||'-')+' | canonical / 정식 거래: '+(r.canonical_numeric_trade_count??0)+' / '+(r.minimum_total_sample??10));
  setv('regimeDirectionCoverage',pct(Number(c.direction_coverage)||0));
  setv('regimeVolCoverage',pct(Number(c.volatility_coverage)||0));
  setv('regimeEvidenceTrades',r.evidence_trade_count??0);
  let best=r.best_observed_direction||r.best_observed_volatility;
  let weak=r.weakest_observed_direction||r.weakest_observed_volatility;
  setv('regimeBest',best?regimeLabel(best.name):'UNOBSERVED / 미관측');
  setv('regimeWeakest',weak?regimeLabel(weak.name):'UNOBSERVED / 미관측');
  document.getElementById('regimeDirectionRows').innerHTML=(r.direction_regimes||[]).map(regimeRow).join('');
  document.getElementById('regimeVolRows').innerHTML=(r.volatility_regimes||[]).map(regimeRow).join('');
  let sources=r.evidence_source_files||[];
  document.getElementById('regimeSources').innerHTML=sources.length?sources.map(x=>'<div>'+x+'</div>').join(''):'No explicit regime evidence source / 명시적 시장환경 증거 출처 없음';
  setv('regimeInterpretation',r.interpretation||'-');
}
async function refreshRegime(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let data=await response.json();
    loadRegime(data);
  }catch(error){
    let e=document.getElementById('regimeInterpretation');
    if(e)e.textContent='Regime load error / 시장환경 로드 오류: '+error;
  }
}
document.addEventListener('DOMContentLoaded',()=>{refreshRegime();setInterval(refreshRegime,30000);});'''

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'id="regimeSection"' in text:
        print("V3.16 REGIME UI ALREADY PRESENT")
        return 0

    marker='<div class="section" id="robustnessSection">\n<h3>Strategy Robustness & Failure Boundary / 전략 견고성 및 실패 경계</h3>\n'
    if marker not in text:
        raise RuntimeError("V3.16 ROBUSTNESS INSERT MARKER NOT FOUND")
    text=text.replace(marker,SECTION+"\n"+marker,1)

    if "</script>" not in text:
        raise RuntimeError("V3.16 SCRIPT END MARKER NOT FOUND")
    text=text.replace("</script>",JS+"\n</script>",1)

    text=text.replace("V3.15 Robustness Boundaries / 견고성 실패 경계","V3.16 Market Regime Analysis / 시장 환경 분석",1)
    target.write_text(text,encoding="utf-8")
    print("V3.16 BILINGUAL REGIME UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
