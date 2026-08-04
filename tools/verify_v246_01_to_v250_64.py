import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ai_strategy_ensemble_v3.engine import evaluate
r = evaluate(ROOT)
checks = {
    "stage": r["stage"] == "V250.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {"AI_STRATEGY_ENSEMBLE_V3_READY", "AI_STRATEGY_ENSEMBLE_V3_REVIEW_REQUIRED"},
    "regime_present": bool(r["market_regime"]["regime"]),
    "scores_present": bool(r["strategy_scores"]),
    "allocations_present": bool(r["allocations"]),
    "candidate_present": bool(r["final_trade_candidate"]),
    "execution_not_authorized": r["final_trade_candidate"].get("execution_authorized") is False,
    "paper_submission_disabled": r["paper_submission_enabled"] is False,
    "live_submission_disabled": r["live_submission_enabled"] is False,
    "broker_write_disabled": r["broker_write_enabled"] is False,
    "paper_orders_zero": r["actual_paper_orders_submitted"] == 0,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "web_api_present": (ROOT / "web_controller/strategy_ensemble_v3_api.py").exists(),
}
failed = [k for k, v in checks.items() if not v]
result = {
    "verification_stage": "V250.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "checks": checks,
    "failed": failed,
    "market_regime": r["market_regime"],
    "strategy_scores": r["strategy_scores"],
    "allocations": r["allocations"],
    "final_trade_candidate": r["final_trade_candidate"],
    "gate": r["gate"],
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
out = ROOT / "release/v246_01_to_v250_64/actual/ai_strategy_ensemble_v3_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
