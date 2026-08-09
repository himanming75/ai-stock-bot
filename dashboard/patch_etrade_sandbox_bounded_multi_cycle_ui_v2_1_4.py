
from pathlib import Path
import argparse

TARGET=Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION="""<div class="section" id="etradeSandboxBoundedV214Section">
<h3>E*TRADE Sandbox Bounded Multi-Cycle V2.1.4 / E*TRADE 샌드박스 제한 반복 사이클 V2.1.4</h3>
<div class="grid">
<div class="card"><h2>Development / 개발</h2><div id="sb214Dev" class="big"></div></div>
<div class="card"><h2>Max Cycles / 최대 사이클</h2><div id="sb214Max" class="big"></div></div>
<div class="card"><h2>Duplicate Guard / 중복 신호 차단</h2><div id="sb214Dup" class="big"></div></div>
<div class="card"><h2>Kill Switch / 긴급 중단</h2><div id="sb214Kill" class="big"></div></div>
<div class="card"><h2>Unbounded Loop / 무한 반복</h2><div id="sb214Loop" class="big"></div></div>
<div class="card"><h2>PROD Orders / PROD 주문</h2><div id="sb214Prod" class="big"></div></div>
</div>
<div class="note">
Maximum 3 cycles / 최대 3회 |
Cooldown enforced / 대기시간 적용 |
Duplicate signals blocked / 중복 신호 차단 |
Kill switch supported / 긴급 중단 지원 |
Unlimited loop prohibited / 무한 반복 금지 |
PROD orders remain locked / PROD 주문 계속 잠금
</div>
</div>"""

JS="""function loadSandboxBoundedV214(d){
 let s=((((d.broker_integration_v1||{}).v2_etrade_readonly_oauth||{}).bounded_multi_cycle_v2_1_4)||{});
 setv('sb214Dev',s.development_status||'-',s.development_status==='COMPLETE'?'PASS':'WAIT');
 setv('sb214Max',String(s.maximum_cycles||'-'));
 setv('sb214Dup',s.duplicate_signal_guard?'ON':'OFF',s.duplicate_signal_guard?'PASS':'WAIT');
 setv('sb214Kill',s.kill_switch_supported?'READY':'NO',s.kill_switch_supported?'PASS':'WAIT');
 setv('sb214Loop',s.unbounded_loop_allowed?'ALLOWED':'BLOCKED',s.unbounded_loop_allowed?'FAIL':'PASS');
 setv('sb214Prod',s.production_order_post_allowed?'UNLOCKED':'LOCKED','FAIL');
}
async function refreshSandboxBoundedV214(){
 try{
  let r=await fetch('/api/status',{cache:'no-store'});
  let d=await r.json();
  loadSandboxBoundedV214(d);
 }catch(e){}
}
document.addEventListener('DOMContentLoaded',()=>{
 refreshSandboxBoundedV214();
 setInterval(refreshSandboxBoundedV214,30000);
});"""

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()

    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'id="etradeSandboxBoundedV214Section"' not in text:
        anchor='<div class="section" id="etradeSandboxAutonomousV213Section">'
        idx=text.find(anchor)
        if idx<0:
            raise RuntimeError("V2.1.4 UI ANCHOR NOT FOUND")
        text=text[:idx]+SECTION+"\\n"+text[idx:]

    if 'function loadSandboxBoundedV214(d)' not in text:
        anchor='function loadSandboxAutoV213(d){'
        idx=text.find(anchor)
        if idx<0:
            idx=text.find('</script>')
        if idx<0:
            raise RuntimeError("V2.1.4 SCRIPT ANCHOR NOT FOUND")
        text=text[:idx]+JS+"\\n"+text[idx:]

    target.write_text(text,encoding="utf-8")
    print("V2.1.4 BILINGUAL UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
