from pathlib import Path
import json,tempfile,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from broker_integration_v1.manual_sandbox_review_packet_builder_v2_1_18 import ManualSandboxReviewPacketBuilderV2118

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/"runtime"/"sandbox_readiness_gate_v2_1_17"
    p.mkdir(parents=True,exist_ok=True)
    row={
        "evidence_key":"fixture-corrected",
        "source_observed_at_utc":"2026-08-10T14:01:00+00:00",
        "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
        "ready":True,
        "reasons":[],
        "eligible_signal_count":1,
        "signals":[{"symbol":"SPY","side":"SELL","quantity":"1","strategy_id":"FIXTURE","source_confidence":"0.80","source_reward_risk":"1.20"}],
        "generic_etrade_bridge_min_confidence":"0.60",
        "canonical_min_confidence":"0.75",
        "canonical_min_reward_risk":"1.0",
        "canonical_paper_gate_semantics":"CORRECTED_V2_1_19_1",
        "manual_review_required":True,
        "automatic_sandbox_execution_allowed":False,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }
    (p/"qualification_ledger.jsonl").write_text(json.dumps(row)+"\n",encoding="utf-8")
    r=ManualSandboxReviewPacketBuilderV2118(td).build()
    print("STATUS:",r["status"])
    print("READY ROWS:",r["ready_rows"])
    print("NEW PACKETS:",r["new_packets"])
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    assert r["new_packets"]==1
print("V2.1.18 CORRECTED FIXTURE: PASS")
