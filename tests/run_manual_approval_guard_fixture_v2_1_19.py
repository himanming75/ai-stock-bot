from pathlib import Path
from datetime import datetime,timezone
import json,tempfile,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from broker_integration_v1.manual_approval_record_expiration_guard_v2_1_19 import ManualApprovalRecordExpirationGuardV2119,APPROVAL_PHRASE

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/"runtime"/"manual_sandbox_review_packets_v2_1_18"
    p.mkdir(parents=True,exist_ok=True)
    packet={
        "packet_status":"AWAITING_MANUAL_REVIEW","evidence_key":"fixture-corrected",
        "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
        "generic_etrade_bridge_min_confidence":"0.60","canonical_min_confidence":"0.75",
        "canonical_min_reward_risk":"1.0","canonical_paper_gate_semantics":"CORRECTED_V2_1_19_1",
        "eligible_signal_count":1,
        "signals":[{"symbol":"SPY","side":"SELL","quantity":"1","strategy_id":"FIXTURE","source_confidence":"0.80","source_reward_risk":"1.20"}],
        "manual_review_required":True,"manual_approval_recorded":False,
        "automatic_sandbox_execution_allowed":False,"broker_orders_submitted":0,
        "production_order_submission":False,"live_trading":False,
    }
    (p/"review_packet_fixture-corrected.json").write_text(json.dumps(packet),encoding="utf-8")
    now=datetime(2026,8,10,14,10,tzinfo=timezone.utc)
    g=ManualApprovalRecordExpirationGuardV2119(td,now_fn=lambda:now)
    r=g.approve("fixture-corrected",APPROVAL_PHRASE)
    print("STATUS:",r["status"])
    print("CANONICAL SEMANTICS:",r.get("canonical_paper_gate_semantics"))
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    assert r["status"]=="PASS_MANUAL_APPROVAL_RECORDED"
print("V2.1.19 CORRECTED FIXTURE: PASS")
