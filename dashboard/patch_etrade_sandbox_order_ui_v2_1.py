
from pathlib import Path
import argparse
TARGET=Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION='''<div class="section" id="etradeSandboxOrderV21Section">
<h3>E*TRADE Sandbox Order Simulation V2.1 / E*TRADE 샌드박스 주문 시뮬레이션 V2.1</h3>
<div class="grid">
<div class="card"><h2>Development / 개발</h2><div id="sb21Dev" class="big"></div></div>
<div class="card"><h2>Environment / 환경</h2><div id="sb21Env" class="big"></div></div>
<div class="card"><h2>Preview / 주문 미리보기</h2><div id="sb21Preview" class="big"></div></div>
<div class="card"><h2>Place / 주문전송</h2><div id="sb21Place" class="big"></div></div>
<div class="card"><h2>PROD Orders / PROD 주문</h2><div id="sb21Prod" class="big"></div></div>
<div class="card"><h2>Profit Validation / 수익성 검증</h2><div id="sb21Profit" class="big"></div></div>
</div>
<div class="note">
Sandbox only / 샌드박스 전용 |
No real securities or money / 실제 증권·자금 이동 없음 |
Preview before Place / Preview 후 Place |
Production order POST remains blocked / PROD 주문 POST 계속 차단
</div>
</div>'''

JS=r'''function loadSandboxOrderV21(d){
 let s=((((d.broker_integration_v1||{}).v2_etrade_readonly_oauth||{}).sandbox_order_v2_1)||{});
 setv('sb21Dev',s.development_status||'-',s.development_status==='COMPLETE'?'PASS':'WAIT');
 setv('sb21Env',s.environment||'-');
 setv('sb21Preview',s.equity_preview_supported?'READY':'NO',s.equity_preview_supported?'PASS':'WAIT');
 setv('sb21Place',s.equity_place_supported?'READY':'NO',s.equity_place_supported?'PASS':'WAIT');
 setv('sb21Prod',s.production_order_post_allowed?'UNLOCKED':'LOCKED','FAIL');
 setv('sb21Profit',s.strategy_profitability_validated?'VALIDATED':'NOT VALIDATED','WAIT');
}
async function refreshSandboxOrderV21(){
 try{
  let response=await fetch('/api/status',{cache:'no-store'});
  let data=await response.json();
  loadSandboxOrderV21(data);
 }catch(error){}
}
document.addEventListener('DOMContentLoaded',()=>{
 refreshSandboxOrderV21();
 setInterval(refreshSandboxOrderV21,30000);
});'''

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",default=r"C:\stock-bot")
 a=p.parse_args()
 target=Path(a.root)/TARGET
 text=target.read_text(encoding="utf-8")
 if 'id="etradeSandboxOrderV21Section"' not in text:
  anchor='<div class="section" id="brokerIntegrationV2Section">'
  idx=text.find(anchor)
  if idx<0: raise RuntimeError("V2.1 UI SECTION ANCHOR NOT FOUND")
  text=text[:idx]+SECTION+"\n"+text[idx:]
 if 'function loadSandboxOrderV21(d)' not in text:
  anchor='function loadBrokerIntegrationV2(d){'
  idx=text.find(anchor)
  if idx<0:
   idx=text.find('</script>')
   if idx<0: raise RuntimeError("V2.1 UI SCRIPT ANCHOR NOT FOUND")
  text=text[:idx]+JS+"\n"+text[idx:]
 target.write_text(text,encoding="utf-8")
 print("V2.1 BILINGUAL UI: PASS")
 return 0

if __name__=="__main__":
 raise SystemExit(main())
