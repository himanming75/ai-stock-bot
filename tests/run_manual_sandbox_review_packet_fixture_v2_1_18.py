from pathlib import Path
import json,tempfile,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.manual_sandbox_review_packet_builder_v2_1_18 import (
    ManualSandboxReviewPacketBuilderV2118,
)

with tempfile.TemporaryDirectory() as td:
    p=Path(td)/"runtime"/"sandbox_readiness_gate_v2_1_17"
    p.mkdir(parents=True,exist_ok=True)
    row={
        "stage":"V2.1.17",
        "source_observed_at_utc":"2026-08-10T14:01:00+00:00",
        "evidence_key":"fixture-ready-001",
        "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
        "ready":True,
        "reasons":[],
        "eligible_signal_count":1,
        "signals":[{
            "symbol":"SPY",
            "side":"SELL",
            "quantity":"1",
            "strategy_id":"FIXTURE",
            "source_confidence":"0.66",
        }],
        "canonical_min_confidence":"0.60",
        "manual_review_required":True,
        "automatic_sandbox_execution_allowed":False,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }
    (p/"qualification_ledger.jsonl").write_text(json.dumps(row)+"\n",encoding="utf-8")
    r=ManualSandboxReviewPacketBuilderV2118(td).build()
    print("STATUS:",r["status"])
    print("SOURCE ROWS:",r["source_rows"])
    print("READY ROWS:",r["ready_rows"])
    print("NEW PACKETS:",r["new_packets"])
    print("MANUAL REVIEW REQUIRED:",r["manual_review_required"])
    print("AUTO SANDBOX EXECUTION:",r["automatic_sandbox_execution_allowed"])
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    print("PROD:",r["production_order_submission"])
    print("LIVE:",r["live_trading"])
    assert r["new_packets"]==1
    assert r["broker_orders_submitted"]==0

print("V2.1.18 SYNTHETIC REVIEW PACKET: PASS")
