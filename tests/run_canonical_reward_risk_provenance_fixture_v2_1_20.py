from pathlib import Path
import json,tempfile,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.canonical_reward_risk_provenance_bridge_v2_1_20 import (
    CanonicalRewardRiskProvenanceBridgeV2120,
)
from broker_integration_v1.evidence_qualification_sandbox_readiness_gate_v2_1_17 import (
    qualify_evidence_row_v2_1_17,
)

with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    ep=root/"runtime"/"fresh_eligible_signal_evidence_v2_1_16"
    cp=root/"runtime"/"real_market_multitimeframe_shadow"
    ep.mkdir(parents=True)
    cp.mkdir(parents=True)

    evidence={
        "stage":"V2.1.16",
        "evidence_key":"fixture-rr-001",
        "observed_at_utc":"2026-08-10T14:00:00+00:00",
        "observer_state":"OBSERVED_FRESH",
        "canonical_gate_aligned":True,
        "eligible_signal_count":1,
        "eligible_signals":[{
            "symbol":"MSFT","side":"BUY","quantity":"1",
            "strategy_id":"V79","source_confidence":"0.65",
        }],
        "signal_capture_allowed":True,
        "freshness_status":"PASS_REGULAR_WINDOW_FRESH_BARS",
        "all_fresh":True,
        "evidence_only":True,
        "broker_orders_submitted":0,
        "production_order_submission":False,
        "live_trading":False,
    }
    (ep/"eligible_signal_evidence.jsonl").write_text(
        json.dumps(evidence)+"\n",encoding="utf-8"
    )

    report={
        "stage":"REAL_MARKET_MULTI_TIMEFRAME_SHADOW_ADAPTER_V1_2",
        "status":"PASS",
        "mode":"SHADOW_ANALYSIS_ONLY",
        "generated_at_utc":"2026-08-10T14:00:00+00:00",
        "source_dataset":"runtime/real_historical_ingestion/alpaca_real_historical_1min.jsonl",
        "canonical_engine":"multi_timeframe_ai.engine.analyze_symbol",
        "canonical_selector":"paper_autonomous_execution.signals.select_candidate",
        "thresholds":{"min_confidence":0.75,"min_reward_risk":1.0},
        "analyses":[{
            "symbol":"MSFT",
            "action":"BUY",
            "reward_risk":1.25,
            "confidence_calibration":{"calibrated_confidence":0.82},
        }],
    }
    (cp/"latest_real_market_shadow.json").write_text(
        json.dumps(report),encoding="utf-8"
    )

    b=CanonicalRewardRiskProvenanceBridgeV2120(td).build()
    row=json.loads(Path(b["latest_output"]).read_text(encoding="utf-8"))
    q=qualify_evidence_row_v2_1_17(row)

    print("BRIDGE STATUS:",b["status"])
    print("PROVENANCE VALID:",row["canonical_reward_risk_provenance_valid"])
    print("CANONICAL CONFIDENCE:",row["eligible_signals"][0]["source_confidence"])
    print("CANONICAL RR:",row["eligible_signals"][0]["source_reward_risk"])
    print("QUALIFICATION:",q["qualification_status"])
    print("BROKER ORDERS:",b["broker_orders_submitted"])
    print("PROD:",b["production_order_submission"])
    print("LIVE:",b["live_trading"])

    assert q["ready"] is True
    assert b["broker_orders_submitted"]==0

print("V2.1.20 END-TO-END SYNTHETIC PROVENANCE: PASS")
