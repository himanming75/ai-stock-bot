from pathlib import Path
import json,tempfile,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from broker_integration_v1.alpaca_paper_bounded_execution_bridge_v2_1_22 import (
    AlpacaPaperBoundedExecutionBridgeV2122,
)

with tempfile.TemporaryDirectory() as td:
    root=Path(td)

    profile_dir=(
        root/"release"/"v14001_15000_paper_autonomous_execution"/"config"
    )
    profile_dir.mkdir(parents=True,exist_ok=True)
    (profile_dir/"paper_execution_profile.json").write_text(
        json.dumps({
            "profile_name":"PAPER_AUTONOMOUS_VALIDATION_V1",
            "paper_submission_enabled":True,
            "live_submission_enabled":False,
            "max_orders_per_session":1,
            "max_notional_per_order":25.0,
            "allowed_symbols":["AAPL","MSFT","NVDA","SPY"],
            "min_confidence":0.75,
            "min_reward_risk":1.0,
            "poll_seconds":30,
            "require_market_open":True,
            "require_manual_arm_token":True,
        }),
        encoding="utf-8",
    )

    evidence="fixture-current-ready-001"
    p21=root/"runtime"/"actual_intraday_canonical_e2e_v2_1_21"
    pq=root/"runtime"/"sandbox_readiness_gate_v2_1_17"
    ps=root/"runtime"/"real_market_multitimeframe_shadow"
    for p in (p21,pq,ps):
        p.mkdir(parents=True,exist_ok=True)

    q={
        "evidence_key":evidence,
        "ready":True,
        "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
        "canonical_paper_gate_semantics":"CORRECTED_V2_1_19_1",
        "canonical_min_confidence":"0.75",
        "canonical_min_reward_risk":"1.0",
        "signals":[{
            "symbol":"AAPL","side":"BUY","quantity":"1",
            "strategy_id":"FIXTURE",
            "source_confidence":"0.82",
            "source_reward_risk":"1.25",
        }],
    }
    (pq/"latest_qualification.json").write_text(
        json.dumps(q),encoding="utf-8"
    )

    (p21/"latest_validation.json").write_text(
        json.dumps({
            "status":"PASS_ACTUAL_INTRADAY_CANONICAL_READY",
            "ready_for_manual_sandbox_review":True,
            "latest_qualification":{
                "evidence_key":evidence,
                "ready":True,
                "qualification_status":"READY_FOR_MANUAL_SANDBOX_REVIEW",
            },
            "broker_orders_submitted":0,
            "production_order_submission":False,
            "live_trading":False,
        }),
        encoding="utf-8",
    )

    (ps/"latest_real_market_shadow.json").write_text(
        json.dumps({
            "analyses":[{
                "symbol":"AAPL",
                "action":"BUY",
                "execution_mode":"ANALYSIS_ONLY",
                "reward_risk":1.25,
                "consensus_score":0.7,
                "confidence_calibration":{
                    "calibrated_confidence":0.82
                },
            }],
        }),
        encoding="utf-8",
    )

    r=AlpacaPaperBoundedExecutionBridgeV2122(root).build_plan()

    print("STATUS:",r["status"])
    print("SYMBOL:",r["selected_candidate"]["symbol"])
    print("SIDE:",r["selected_candidate"]["side"])
    print("CONFIDENCE:",r["selected_candidate"]["confidence"])
    print("REWARD/RISK:",r["selected_candidate"]["reward_risk"])
    print("MAX NOTIONAL:",r["maximum_notional_per_order"])
    print("PAPER ORDER SUBMITTED:",r["paper_order_submitted"])
    print("LIVE ORDER SUBMITTED:",r["live_order_submitted"])

    assert r["status"]=="READY_FOR_BOUNDED_ALPACA_PAPER_SUBMISSION"
    assert r["paper_order_submitted"] is False

print("V2.1.22 SYNTHETIC DRY PLAN: PASS")
