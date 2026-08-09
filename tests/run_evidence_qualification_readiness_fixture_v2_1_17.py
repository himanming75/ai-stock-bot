from pathlib import Path
import json,tempfile,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.evidence_qualification_sandbox_readiness_gate_v2_1_17 import (
    EvidenceQualificationSandboxReadinessGateV2117,
)

with tempfile.TemporaryDirectory() as td:
    p=(
        Path(td)
        /"runtime"
        /"fresh_eligible_signal_evidence_v2_1_16"
    )
    p.mkdir(parents=True,exist_ok=True)

    row={
        "stage":"V2.1.16",
        "evidence_key":"fixture-ready-001",
        "observed_at_utc":"2026-08-10T14:01:00+00:00",
        "observer_state":"OBSERVED_FRESH",
        "canonical_gate_aligned":True,
        "eligible_signal_count":1,
        "eligible_signals":[{
            "symbol":"SPY",
            "side":"SELL",
            "quantity":"1",
            "strategy_id":"FIXTURE",
            "source_confidence":"0.66",
        }],
        "signal_capture_allowed":True,
        "freshness_status":"PASS_REGULAR_WINDOW_FRESH_BARS",
        "all_fresh":True,
        "evidence_only":True,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }

    (p/"eligible_signal_evidence.jsonl").write_text(
        json.dumps(row)+"\n",
        encoding="utf-8",
    )

    r=EvidenceQualificationSandboxReadinessGateV2117(td).evaluate()
    print("STATUS:",r["status"])
    print("SOURCE ROWS:",r["source_rows"])
    print("READY ROWS:",r["ready_rows"])
    print("NOT READY ROWS:",r["not_ready_rows"])
    print("NEW QUALIFICATIONS:",r["new_qualification_rows"])
    print("MANUAL REVIEW REQUIRED:",r["manual_review_required"])
    print("AUTO SANDBOX EXECUTION:",r["automatic_sandbox_execution_allowed"])
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    print("PROD:",r["production_order_submission"])
    print("LIVE:",r["live_trading"])
    assert r["ready_rows"]==1
    assert r["automatic_sandbox_execution_allowed"] is False
    assert r["broker_orders_submitted"]==0

print("V2.1.17 SYNTHETIC READINESS GATE: PASS")
