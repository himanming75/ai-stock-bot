from pathlib import Path
import argparse

TARGET=Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION="""<div class="section" id="etradeAISignalDecisionV215Section">
<h3>AI Signal Decision Bridge V2.1.5 / AI 신호 결정 브리지 V2.1.5</h3>
<div class="grid">
<div class="card"><h2>Development / 개발</h2><div id="sb215Dev" class="big"></div></div>
<div class="card"><h2>BUY/SELL/HOLD / 매수·매도·보류</h2><div id="sb215Decision" class="big"></div></div>
<div class="card"><h2>Confidence Gate / 신뢰도 게이트</h2><div id="sb215Confidence" class="big"></div></div>
<div class="card"><h2>HOLD Blocks Orders / HOLD 주문 차단</h2><div id="sb215Hold" class="big"></div></div>
<div class="card"><h2>Max Signal Queue / 최대 신호 큐</h2><div id="sb215Queue" class="big"></div></div>
<div class="card"><h2>PROD Orders / PROD 주문</h2><div id="sb215Prod" class="big"></div></div>
</div>
<div class="note">
Strategy recommendation is validated, not invented / 전략 추천은 검증만 하고 새로 추측하지 않음 |
HOLD and low-confidence signals do not become orders / HOLD 및 낮은 신뢰도는 주문으로 전환 안 함 |
V2.1.4 bounded controller reused / V2.1.4 제한 반복 컨트롤러 재사용 |
PROD orders remain locked / PROD 주문 계속 잠금
</div>
</div>"""

JS="""function loadAISignalDecisionV215(d){
 let s=((((d.broker_integration_v1||{}).v2_etrade_readonly_oauth||{}).ai_signal_decision_v2_1_5)||{});
 setv('sb215Dev',s.development_status||'-',s.development_status==='COMPLETE'?'PASS':'WAIT');
 setv('sb215Decision',s.buy_sell_hold_normalization?'READY':'NO',s.buy_sell_hold_normalization?'PASS':'WAIT');
 setv('sb215Confidence',s.confidence_gate?'ON':'OFF',s.confidence_gate?'PASS':'WAIT');
 setv('sb215Hold',s.hold_blocks_order?'ON':'OFF',s.hold_blocks_order?'PASS':'WAIT');
 setv('sb215Queue',String(s.bounded_signal_queue_maximum||'-'));
 setv('sb215Prod',s.production_order_post_allowed?'UNLOCKED':'LOCKED','FAIL');
}
async function refreshAISignalDecisionV215(){
 try{
  let r=await fetch('/api/status',{cache:'no-store'});
  let d=await r.json();
  loadAISignalDecisionV215(d);
 }catch(e){}
}
document.addEventListener('DOMContentLoaded',()=>{
 refreshAISignalDecisionV215();
 setInterval(refreshAISignalDecisionV215,30000);
});"""

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'id="etradeAISignalDecisionV215Section"' not in text:
        anchor='<div class="section" id="etradeSandboxBoundedV214Section">'
        idx=text.find(anchor)
        if idx<0:
            raise RuntimeError("V2.1.5 UI ANCHOR NOT FOUND")
        text=text[:idx]+SECTION+"\n"+text[idx:]

    if 'function loadAISignalDecisionV215(d)' not in text:
        anchor='function loadSandboxBoundedV214(d){'
        idx=text.find(anchor)
        if idx<0:
            idx=text.find('</script>')
        if idx<0:
            raise RuntimeError("V2.1.5 SCRIPT ANCHOR NOT FOUND")
        text=text[:idx]+JS+"\n"+text[idx:]

    target.write_text(text,encoding="utf-8")
    print("V2.1.5 BILINGUAL UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
