from pathlib import Path
import argparse

TARGET=Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION = """<div class="section" id="etradeSandboxAutonomousV213Section">
<h3>E*TRADE Sandbox Autonomous Cycle V2.1.3 / E*TRADE 샌드박스 자동 사이클 V2.1.3</h3>
<div class="grid">
<div class="card"><h2>Development / 개발</h2><div id="sb213Dev" class="big"></div></div>
<div class="card"><h2>One Cycle / 1회 자동 사이클</h2><div id="sb213Cycle" class="big"></div></div>
<div class="card"><h2>Auto Repeat / 자동 반복</h2><div id="sb213Repeat" class="big"></div></div>
<div class="card"><h2>PROD Orders / PROD 주문</h2><div id="sb213Prod" class="big"></div></div>
</div>
<div class="note">
One-cycle automation only / 1회 자동 사이클만 |
Existing Preview+Place+Ledger+Reconciliation reused / 기존 구성 재사용 |
Automatic repeat remains disabled / 자동 반복 비활성 |
PROD orders remain locked / PROD 주문 계속 잠금
</div>
</div>"""

JS = r"""function loadSandboxAutoV213(d){
 let s=((((d.broker_integration_v1||{}).v2_etrade_readonly_oauth||{}).autonomous_cycle_v2_1_3)||{});
 setv('sb213Dev',s.development_status||'-',s.development_status==='COMPLETE'?'PASS':'WAIT');
 setv('sb213Cycle',s.one_cycle_supported?'READY':'NO',s.one_cycle_supported?'PASS':'WAIT');
 setv('sb213Repeat',s.automatic_repeat_enabled?'ENABLED':'DISABLED','WAIT');
 setv('sb213Prod',s.production_order_post_allowed?'UNLOCKED':'LOCKED','FAIL');
}
async function refreshSandboxAutoV213(){
 try{
  let r=await fetch('/api/status',{cache:'no-store'});
  let d=await r.json();
  loadSandboxAutoV213(d);
 }catch(e){}
}
document.addEventListener('DOMContentLoaded',()=>{
 refreshSandboxAutoV213();
 setInterval(refreshSandboxAutoV213,30000);
});"""

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'id="etradeSandboxAutonomousV213Section"' not in text:
        anchor='<div class="section" id="etradeSandboxOrderV212Section">'
        idx=text.find(anchor)
        if idx<0:
            raise RuntimeError("V2.1.3 UI ANCHOR NOT FOUND")
        text=text[:idx]+SECTION+"\n"+text[idx:]

    if 'function loadSandboxAutoV213(d)' not in text:
        anchor='function loadSandboxOrderV212(d){'
        idx=text.find(anchor)
        if idx<0:
            idx=text.find('</script>')
        if idx<0:
            raise RuntimeError("V2.1.3 SCRIPT ANCHOR NOT FOUND")
        text=text[:idx]+JS+"\n"+text[idx:]

    target.write_text(text,encoding="utf-8")
    print("V2.1.3 BILINGUAL UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
