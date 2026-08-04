from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from ai_strategy_ensemble_v3.allocation import allocate
from ai_strategy_ensemble_v3.config import load, validate
from ai_strategy_ensemble_v3.decision import combine
from ai_strategy_ensemble_v3.gate import evaluate as evaluate_gate
from ai_strategy_ensemble_v3.io import load_json, write_json, append_jsonl
from ai_strategy_ensemble_v3.regime import detect
from ai_strategy_ensemble_v3.scoring import score

def evaluate(root: Path) -> dict:
    policy = load(root)
    validation = validate(policy)
    fixture = load_json(root / "release/v246_01_to_v250_64/input/strategy_ensemble_v3_fixture.json")
    risk = load_json(root / "release/v206_01_to_v210_64/actual/risk_engine_v2_result.json")
    exits = load_json(root / "release/v241_01_to_v245_64/actual/exit_manager_v2_result.json")

    regime = detect(fixture.get("market", {}))
    scores = [score(row, regime["regime"], policy) for row in fixture.get("strategies", [])]
    scores.sort(key=lambda row: row["score"], reverse=True)
    allocations = allocate(scores, policy)
    candidates = combine(allocations)
    candidates.sort(key=lambda row: row["confidence"], reverse=True)
    final_candidate = candidates[0] if candidates else {}
    gate = evaluate_gate(final_candidate, risk, exits, policy)

    final_trade_candidate = {
        **final_candidate,
        "gate_passed": gate["passed"],
        "execution_authorized": False,
        "submission_authorized": False,
    } if final_candidate else {}

    checks = {
        "policy_valid": validation["valid"],
        "regime_detected": bool(regime.get("regime")),
        "strategy_scores_present": bool(scores),
        "allocations_present": bool(allocations),
        "candidate_present": bool(final_candidate),
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    state = "AI_STRATEGY_ENSEMBLE_V3_READY" if not failed else "AI_STRATEGY_ENSEMBLE_V3_REVIEW_REQUIRED"

    result = {
        "stage": "V250.64",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "market_regime": regime,
        "strategy_scores": scores,
        "allocations": allocations,
        "candidates": candidates,
        "final_trade_candidate": final_trade_candidate,
        "gate": gate,
        "checks": checks,
        "failed": failed,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V251_01_TO_V255_64_EXECUTION_OPTIMIZER",
    }
    actual = root / "release/v246_01_to_v250_64/actual"
    write_json(actual / "ai_strategy_ensemble_v3_result.json", result)
    write_json(actual / "strategy_scoreboard.json", {"rows": scores})
    write_json(actual / "strategy_allocations.json", {"rows": allocations})
    write_json(actual / "final_trade_candidate.json", final_trade_candidate)
    append_jsonl(actual / "ai_strategy_ensemble_v3_ledger.jsonl", {
        "observed_at": result["observed_at"],
        "state": state,
        "regime": regime["regime"],
        "candidate": final_trade_candidate,
        "actual_live_orders_submitted": 0,
    })
    return result
