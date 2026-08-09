from pathlib import Path
import argparse

TARGET=Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION="""<div class="section" id="etradeCurrentMarketSignalV217Section">
<h3>Current Market Data Signal Bridge V2.1.7 / 현재 시장 데이터 신호 브리지 V2.1.7</h3>
<div class="grid">
<div class="card"><h2>Development / 개발</h2><div id="sb217Dev" class="big"></div></div>
<div class="card"><h2>Market Data Engine / 시장 데이터 엔진</h2><div id="sb217Market" class="big"></div></div>
<div class="card"><h2>Indicator Engine / 지표 엔진</h2><div id="sb217Indicator" class="big"></div></div>
<div class="card"><h2>Signal Engine / 신호 엔진</h2><div id="sb217Signal" class="big"></div></div>
<div class="card"><h2>Read-Only Source / 읽기 전용 소스</h2><div id="sb217Readonly" class="big"></div></div>
<div class="card"><h2>PROD Orders / PROD 주문</h2><div id="sb217Prod" class="big"></div></div>
</div>
<div class="note">
Existing V102/V103 market-data engine reused / 기존 V102/V103 시장 데이터 엔진 재사용 |
Existing V79 indicator and signal engines reused / 기존 V79 지표·신호 엔진 재사용 |
Network requires explicit opt-in / 네트워크 연결은 명시적 승인 필요 |
This stage submits no broker orders / 이 단계는 브로커 주문을 제출하지 않음 |
PROD orders remain locked / PROD 주문 계속 잠금
</div>
</div>"""

JS="""function loadCurrentMarketSignalV217(d){
 let s=((((d.broker_integration_v1||{}).v2_etrade_readonly_oauth||{}).current_market_data_signal_v2_1_7)||{});
 setv('sb217Dev',s.development_status||'-',s.development_status==='COMPLETE'?'PASS':'WAIT');
 setv('sb217Market',s.existing_market_data_engine_reused||'-','PASS');
 setv('sb217Indicator',s.existing_indicator_engine_reused||'-','PASS');
 setv('sb217Signal',s.existing_signal_engine_reused||'-','PASS');
 setv('sb217Readonly',s.current_readonly_market_data_source_ready?'READY':'NO',s.current_readonly_market_data_source_ready?'PASS':'WAIT');
 setv('sb217Prod',s.production_order_post_allowed?'UNLOCKED':'LOCKED','FAIL');
}
async function refreshCurrentMarketSignalV217(){
 try{
  let r=await fetch('/api/status',{cache:'no-store'});
  let d=await r.json();
  loadCurrentMarketSignalV217(d);
 }catch(e){}
}
document.addEventListener('DOMContentLoaded',()=>{
 refreshCurrentMarketSignalV217();
 setInterval(refreshCurrentMarketSignalV217,30000);
});"""

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'id="etradeCurrentMarketSignalV217Section"' not in text:
        anchor='<div class="section" id="etradeAISignalDecisionV215Section">'
        idx=text.find(anchor)
        if idx<0:
            raise RuntimeError("V2.1.7 UI ANCHOR NOT FOUND")
        text=text[:idx]+SECTION+"\n"+text[idx:]

    if 'function loadCurrentMarketSignalV217(d)' not in text:
        anchor='function loadAISignalDecisionV215(d){'
        idx=text.find(anchor)
        if idx<0:
            idx=text.find('</script>')
        if idx<0:
            raise RuntimeError("V2.1.7 SCRIPT ANCHOR NOT FOUND")
        text=text[:idx]+JS+"\n"+text[idx:]

    target.write_text(text,encoding="utf-8")
    print("V2.1.7 BILINGUAL UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
