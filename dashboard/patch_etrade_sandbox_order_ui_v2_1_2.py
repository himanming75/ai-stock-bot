
from pathlib import Path
import argparse

TARGET=Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION='''<div class="section" id="etradeSandboxOrderV212Section">
<h3>E*TRADE Sandbox Place + Ledger + Reconciliation V2.1.2 / E*TRADE 샌드박스 Place + 원장 + 대사 V2.1.2</h3>

<div class="grid">
<div class="card"><h2>Development / 개발</h2><div id="sb212Dev" class="big"></div></div>
<div class="card"><h2>Sandbox Place / 샌드박스 주문전송</h2><div id="sb212Place" class="big"></div></div>
<div class="card"><h2>Order Ledger / 주문 원장</h2><div id="sb212Ledger" class="big"></div></div>
<div class="card"><h2>Reconciliation / 주문 대사</h2><div id="sb212Recon" class="big"></div></div>
<div class="card"><h2>PROD Orders / PROD 주문</h2><div id="sb212Prod" class="big"></div></div>
<div class="card"><h2>Profit Validation / 수익성 검증</h2><div id="sb212Profit" class="big"></div></div>
</div>

<div class="note">
Explicit PLACE confirmation required / PLACE 명시 확인 필요 |
Runtime ledger stores account fingerprint only / 원장에는 계좌 fingerprint만 저장 |
Sandbox GET Orders may return stored sample data / Sandbox 주문조회는 저장 샘플 데이터일 수 있음 |
Production orders remain locked / PROD 주문 계속 잠금
</div>
</div>'''

JS=r'''function loadSandboxOrderV212(d){
 let s=((((d.broker_integration_v1||{}).v2_etrade_readonly_oauth||{}).place_ledger_v2_1_2)||{});
 setv('sb212Dev',s.development_status||'-',s.development_status==='COMPLETE'?'PASS':'WAIT');
 setv('sb212Place',s.sandbox_place_supported?'READY':'NO',s.sandbox_place_supported?'PASS':'WAIT');
 setv('sb212Ledger',s.order_ledger_supported?'READY':'NO',s.order_ledger_supported?'PASS':'WAIT');
 setv('sb212Recon',s.status_reconciliation_supported?'READY':'NO',s.status_reconciliation_supported?'PASS':'WAIT');
 setv('sb212Prod',s.production_order_post_allowed?'UNLOCKED':'LOCKED','FAIL');
 setv('sb212Profit',s.profitability_validation?'VALIDATED':'NOT VALIDATED','WAIT');
}
async function refreshSandboxOrderV212(){
 try{
  let response=await fetch('/api/status',{cache:'no-store'});
  let data=await response.json();
  loadSandboxOrderV212(data);
 }catch(error){}
}
document.addEventListener('DOMContentLoaded',()=>{
 refreshSandboxOrderV212();
 setInterval(refreshSandboxOrderV212,30000);
});'''

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'id="etradeSandboxOrderV212Section"' not in text:
        anchor='<div class="section" id="etradeSandboxOrderV21Section">'
        idx=text.find(anchor)
        if idx<0:
            raise RuntimeError("V2.1.2 UI SECTION ANCHOR NOT FOUND")
        text=text[:idx]+SECTION+"\n"+text[idx:]

    if 'function loadSandboxOrderV212(d)' not in text:
        anchor='function loadSandboxOrderV21(d){'
        idx=text.find(anchor)
        if idx<0:
            idx=text.find('</script>')
            if idx<0:
                raise RuntimeError("V2.1.2 UI SCRIPT ANCHOR NOT FOUND")
        text=text[:idx]+JS+"\n"+text[idx:]

    target.write_text(text,encoding="utf-8")
    print("V2.1.2 BILINGUAL UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
