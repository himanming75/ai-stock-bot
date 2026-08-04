from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from multi_timeframe_strategy.allocation import build as build_allocation
from multi_timeframe_strategy.config import load, validate
from multi_timeframe_strategy.conflicts import resolve
from multi_timeframe_strategy.io import load_json, write_json, append_jsonl
from multi_timeframe_strategy.scoring import score
from multi_timeframe_strategy.timeframes import enrich
from multi_timeframe_strategy.voting import vote

def evaluate(root: Path) -> dict:
    policy = load(root)
    validation = validate(policy)
    fixture = load_json(
        root / "release/v271_01_to_v280_64/input/multi_timeframe_signals.json"
    )
    enriched = [enrich(row, policy) for row in fixture.get("signals", [])]
    scored = [score(row) for row in enriched]
    resolved = resolve(scored, bool(policy.get("allow_same_symbol_across_profiles")))
    allocation = build_allocation(resolved, policy)
    candidates = vote(resolved)
    final_candidate = candidates[0] if candidates else {}

    checks = {
        "policy_valid": validation["valid"],
        "signals_present": bool(scored),
        "profiles_present": bool(policy.get("profiles")),
        "allocation_within_risk": allocation["within_total_risk_limit"],
        "candidate_present": bool(final_candidate),
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    state = (
        "MULTI_TIMEFRAME_STRATEGY_ENSEMBLE_READY"
        if not failed
        else "MULTI_TIMEFRAME_STRATEGY_ENSEMBLE_REVIEW_REQUIRED"
    )
    result = {
        "stage": "V280.64",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "strategy_rows": resolved,
        "allocation": allocation,
        "candidates": candidates,
        "final_candidate": {
            **final_candidate,
            "execution_authorized": False,
            "submission_authorized": False,
        } if final_candidate else {},
        "checks": checks,
        "failed": failed,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V281_01_TO_V290_64_MULTI_ACCOUNT_ENGINE",
    }
    actual = root / "release/v271_01_to_v280_64/actual"
    write_json(actual / "multi_timeframe_strategy_result.json", result)
    write_json(actual / "strategy_profile_scoreboard.json", {"rows": resolved})
    write_json(actual / "strategy_capital_allocation.json", allocation)
    write_json(actual / "ensemble_final_candidate.json", result["final_candidate"])
    append_jsonl(actual / "multi_timeframe_strategy_ledger.jsonl", {
        "observed_at": result["observed_at"],
        "state": state,
        "final_candidate": result["final_candidate"],
        "actual_live_orders_submitted": 0,
    })
    return result
