
from pathlib import Path
import argparse

TARGET=Path("dashboard/templates/operations_dashboard_v3_2.html")

SECTION='''<div class="section" id="brokerIntegrationV2Section">
<h3>Broker Integration V2 - E*TRADE Read-only OAuth / 브로커 연동 V2 - E*TRADE 읽기 전용 OAuth</h3>
<div class="grid">
<div class="card"><h2>Development / 개발</h2><div id="brokerV2Dev" class="big"></div></div>
<div class="card"><h2>OAuth Status / OAuth 상태</h2><div id="brokerV2OAuth" class="big"></div></div>
<div class="card"><h2>Signature Test / 서명 테스트</h2><div id="brokerV2Sig" class="big"></div></div>
<div class="card"><h2>Token Persistence / 토큰 저장</h2><div id="brokerV2Token" class="big"></div></div>
<div class="card"><h2>Network / 네트워크</h2><div id="brokerV2Network" class="big"></div></div>
<div class="card"><h2>Live Trading / 실거래</h2><div id="brokerV2Live" class="big"></div></div>
</div>

<div class="two" style="margin-top:12px">
<div class="card"><h2>Reuse Audit / 재사용 감사</h2><div id="brokerV2Reuse" class="note"></div></div>
<div class="card"><h2>Read-only Safety / 읽기 전용 안전장치</h2><div id="brokerV2Safety" class="note"></div></div>
</div>

<div class="note">
Existing Broker V1 bridge reused / 기존 Broker V1 브리지 재사용 |
Existing E*TRADE read-only adapter reused / 기존 E*TRADE 읽기 전용 어댑터 재사용 |
New credential vault not created / 새 credential vault 생성 안 함 |
OAuth network requires explicit user opt-in / OAuth 네트워크는 사용자 명시적 승인 필요
</div>
</div>'''

JS=r'''function loadBrokerIntegrationV2(d){
  let v=((d.broker_integration_v1||{}).v2_etrade_readonly_oauth)||{};
  let c=v.contracts||{};

  setv('brokerV2Dev',v.development_status||'-',v.development_status==='COMPLETE'?'PASS':'WAIT');
  setv('brokerV2OAuth',v.etrade_oauth_status||'-');
  setv('brokerV2Sig',v.official_signature_vector_pass?'PASS':'FAIL',v.official_signature_vector_pass?'PASS':'FAIL');
  setv('brokerV2Token',v.token_persistence||'-',v.token_persistence==='DISABLED'?'PASS':'WAIT');
  setv('brokerV2Network',v.read_only_network_opt_in_required?'OPT-IN REQUIRED / 승인 필요':'-','WAIT');
  setv('brokerV2Live',v.live_trading_status||'LOCKED','FAIL');

  setv('brokerV2Reuse',
    'V1 bridge reused / V1 재사용: '+(c.v1_bridge_reused?'YES':'NO')+
    ' | V77.1 contract reused / V77.1 재사용: '+(c.canonical_v77_1_contract_reused?'YES':'NO')+
    ' | Existing E*TRADE adapter reused / 기존 E*TRADE 어댑터 재사용: '+(c.existing_etrade_v1_adapter_reused?'YES':'NO')+
    ' | Duplicate contract / 중복 계약: '+(c.duplicate_broker_contract_created?'YES':'NO')
  );

  setv('brokerV2Safety',
    'Order submission / 주문전송: '+(v.order_submission_status||'LOCKED')+
    ' | Cancel/replace / 취소·정정: '+(v.cancel_replace_status||'LOCKED')+
    ' | Live / 실거래: '+(v.live_trading_status||'LOCKED')+
    ' | Access token persisted / 토큰 저장: '+(c.access_token_persisted?'YES':'NO')
  );
}

async function refreshBrokerIntegrationV2(){
  try{
    let response=await fetch('/api/status',{cache:'no-store'});
    let data=await response.json();
    loadBrokerIntegrationV2(data);
  }catch(error){
    let e=document.getElementById('brokerV2Safety');
    if(e)e.textContent='Broker V2 load error / 브로커 V2 로드 오류: '+error;
  }
}
document.addEventListener('DOMContentLoaded',()=>{
  refreshBrokerIntegrationV2();
  setInterval(refreshBrokerIntegrationV2,30000);
});'''

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\stock-bot")
    a=p.parse_args()
    target=Path(a.root)/TARGET
    text=target.read_text(encoding="utf-8")

    if 'id="brokerIntegrationV2Section"' not in text:
        anchor='<div class="section" id="brokerIntegrationV1Section">'
        idx=text.find(anchor)
        if idx<0:
            raise RuntimeError("BROKER V2 UI SECTION ANCHOR NOT FOUND")
        text=text[:idx]+SECTION+"\n"+text[idx:]

    if 'function loadBrokerIntegrationV2(d)' not in text:
        anchor='function loadBrokerIntegrationV1(d){'
        idx=text.find(anchor)
        if idx<0:
            anchor='</script>'
            idx=text.find(anchor)
            if idx<0:
                raise RuntimeError("BROKER V2 UI SCRIPT ANCHOR NOT FOUND")
        text=text[:idx]+JS+"\n"+text[idx:]

    target.write_text(text,encoding="utf-8")
    print("BROKER INTEGRATION V2 BILINGUAL UI: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
