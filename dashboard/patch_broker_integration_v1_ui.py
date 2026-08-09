
from pathlib import Path
import argparse

TARGET=Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION='''<div class="section" id="brokerIntegrationV1Section">
<h3>Broker Integration V1 Bridge / 브로커 연동 V1 브리지</h3>
<div class="grid">
<div class="card"><h2>Development / 개발</h2><div id="brokerV1Dev" class="big"></div></div>
<div class="card"><h2>Canonical Contract / 기존 공통 계약</h2><div id="brokerV1Contract" class="big"></div></div>
<div class="card"><h2>E*TRADE Read-only / E*TRADE 읽기 전용</h2><div id="brokerV1Etrade" class="big"></div></div>
<div class="card"><h2>Network / 네트워크</h2><div id="brokerV1Network" class="big"></div></div>
<div class="card"><h2>Live Trading / 실거래</h2><div id="brokerV1Live" class="big"></div></div>
<div class="card"><h2>Duplicate Components / 중복 구성요소</h2><div id="brokerV1Dup" class="big"></div></div>
</div>

<div style="margin-top:12px">
<h3>Broker Capability Matrix / 브로커 기능 매트릭스</h3>
<div class="scroll-table">
<table>
<thead><tr><th>Broker / 브로커</th><th>Account Read / 계좌 조회</th><th>Positions / 포지션</th><th>Orders / 주문조회</th><th>Submit / 주문전송</th><th>Live / 실거래</th></tr></thead>
<tbody id="brokerV1Rows"></tbody>
</table>
</div>
</div>

<div class="two" style="margin-top:12px">
<div class="card"><h2>Reuse Audit / 재사용 감사</h2><div id="brokerV1Reuse" class="note"></div></div>
<div class="card"><h2>Safety Gateway / 안전 게이트웨이</h2><div id="brokerV1Safety" class="note"></div></div>
</div>

<div class="note">
Existing V77.1 Broker Contract reused / 기존 V77.1 브로커 계약 재사용 |
Existing Alpaca stack reused / 기존 Alpaca 스택 재사용 |
E*TRADE OAuth 1.0a foundation only / E*TRADE OAuth 1.0a 기반만 구축 |
Broker writes remain locked / 브로커 쓰기 잠금 유지
</div>
</div>'''

JS=r'''function loadBrokerIntegrationV1(d){
  let b=d.broker_integration_v1||{};
  let cm=(b.capability_matrix||{}).brokers||{};
  let reuse=b.contract_reuse||{};
  let safety=b.live_safety_gateway||{};

  setv('brokerV1Dev',b.development_status||'-',b.development_status==='COMPLETE'?'PASS':'WAIT');
  setv('brokerV1Contract',reuse.canonical_contract_module||'-');
  setv('brokerV1Etrade',b.etrade_readonly_status||'-',b.etrade_readonly_status==='FOUNDATION_READY'?'PASS':'WAIT');
  setv('brokerV1Network',b.network_status||'LOCKED','FAIL');
  setv('brokerV1Live',b.live_trading_status||'LOCKED','FAIL');

  let dup=((b.contracts||{}).duplicate_broker_contract_created||
           (b.contracts||{}).duplicate_alpaca_market_data_stack_created);
  setv('brokerV1Dup',dup?'FOUND / 발견':'NONE / 없음',dup?'FAIL':'PASS');

  let rows=Object.entries(cm).map(([name,x])=>{
    let acct=x.read_accounts??x.read_account??x.read_account_bridge??false;
    let pos=x.read_positions??x.read_positions_bridge??false;
    let ord=x.read_orders??x.read_orders_bridge??false;
    let submit=x.submit_orders??x.submit_orders_added_by_v1??false;
    return `<tr><td>${name}</td><td>${acct?'YES':'NO'}</td><td>${pos?'YES':'NO'}</td><td>${ord?'YES':'NO'}</td><td>${submit?'YES':'NO'}</td><td>${x.live?'YES':'NO'}</td></tr>`;
  }).join('');

  let t=document.getElementById('brokerV1Rows');
  if(t)t.innerHTML=rows||'<tr><td colspan="6">No broker data / 브로커 데이터 없음</td></tr>';

  setv('brokerV1Reuse',
    'Contract / 계약: '+(reuse.canonical_contract_module||'-')+
    ' | Duplicate contracts / 중복 계약: '+(reuse.duplicate_contracts_created?'YES':'NO')+
    ' | Alpaca duplicate / Alpaca 중복: '+(((b.alpaca_reuse||{}).new_alpaca_market_data_client_created)?'YES':'NO')
  );

  setv('brokerV1Safety',
    'Broker write / 브로커 쓰기: '+(safety.broker_write_locked?'LOCKED':'UNLOCKED')+
    ' | Order submit / 주문전송: '+(safety.order_submission_locked?'LOCKED':'UNLOCKED')+
    ' | Cancel/replace / 취소·정정: '+(safety.cancel_replace_locked?'LOCKED':'UNLOCKED')+
    ' | Live / 실거래: '+(safety.live_trading_locked?'LOCKED':'UNLOCKED')
  );
}

async function refreshBrokerIntegrationV1(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let data=await response.json();
    loadBrokerIntegrationV1(data);
  }catch(error){
    let e=document.getElementById('brokerV1Safety');
    if(e)e.textContent='Broker V1 load error / 브로커 V1 로드 오류: '+error;
  }
}

document.addEventListener('DOMContentLoaded',()=>{
  refreshBrokerIntegrationV1();
  setInterval(refreshBrokerIntegrationV1,30000);
});'''

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'id="brokerIntegrationV1Section"' not in text:
        anchor='<div class="section" id="aiEngineV2Section">'
        idx=text.find(anchor)
        if idx<0:
            raise RuntimeError("BROKER V1 UI SECTION ANCHOR NOT FOUND")
        text=text[:idx]+SECTION+"\n"+text[idx:]

    if 'function loadBrokerIntegrationV1(d)' not in text:
        anchor='function loadAiEngineV2(d){'
        idx=text.find(anchor)
        if idx<0:
            anchor='</script>'
            idx=text.find(anchor)
            if idx<0:
                raise RuntimeError("BROKER V1 UI SCRIPT ANCHOR NOT FOUND")
        text=text[:idx]+JS+"\n"+text[idx:]

    target.write_text(text,encoding="utf-8")
    print("BROKER INTEGRATION V1 BILINGUAL UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
