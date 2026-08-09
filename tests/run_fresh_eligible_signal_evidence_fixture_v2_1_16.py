from pathlib import Path
import json,tempfile,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.fresh_eligible_signal_evidence_capture_v2_1_16 import (
    FreshEligibleSignalEvidenceCaptureV2116,
)

with tempfile.TemporaryDirectory() as td:
    p=(
        Path(td)
        /"runtime"
        /"freshness_guarded_persistent_observer_v2_1_15"
    )
    p.mkdir(parents=True,exist_ok=True)

    row={
        "stage":"V2.1.15",
        "observed_at_utc":"2026-08-10T14:01:00+00:00",
        "iteration":7,
        "observer_state":"OBSERVED_FRESH",
        "snapshot_fingerprint":"fixture-eligible-001",
        "eligible_signal_captured":True,
        "session_freshness_gate":{
            "status":"PASS_REGULAR_WINDOW_FRESH_BARS"
        },
        "snapshot":{
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
            "market_data_fetch_skipped":False,
            "freshness_status":"PASS_REGULAR_WINDOW_FRESH_BARS",
            "all_fresh":True,
        },
    }

    (p/"observation_ledger.jsonl").write_text(
        json.dumps(row)+"\n",
        encoding="utf-8",
    )

    r=FreshEligibleSignalEvidenceCaptureV2116(td).capture()
    print("STATUS:",r["status"])
    print("SOURCE ROWS:",r["source_rows"])
    print("ELIGIBLE FOUND:",r["eligible_rows_found"])
    print("NEW EVIDENCE:",r["new_evidence_rows"])
    print("DUPLICATES:",r["duplicate_evidence_rows"])
    print("BROKER ORDERS:",r["broker_orders_submitted"])
    print("PROD:",r["production_order_submission"])
    print("LIVE:",r["live_trading"])
    assert r["new_evidence_rows"]==1
    assert r["broker_orders_submitted"]==0

print("V2.1.16 SYNTHETIC EVIDENCE CAPTURE: PASS")
