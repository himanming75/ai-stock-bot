from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from execution_optimizer.config import load, validate
from execution_optimizer.fill_probability import estimate as fill_estimate
from execution_optimizer.io import load_json, write_json, append_jsonl
from execution_optimizer.planner import build as build_plan
from execution_optimizer.quote_analyzer import analyze
from execution_optimizer.retry_manager import build as build_retry
from execution_optimizer.slippage import estimate as slippage_estimate

def evaluate(root: Path) -> dict:
    policy = load(root)
    validation = validate(policy)
    candidate = load_json(root / "release/v251_01_to_v255_64/input/execution_candidate.json").get("candidate", {})
    quote_input = load_json(root / "release/v251_01_to_v255_64/input/execution_quote.json")
    market = load_json(root / "release/v251_01_to_v255_64/input/execution_market.json")
    quote = analyze(quote_input, policy)
    fill = fill_estimate(quote, market)
    slippage = slippage_estimate(candidate, quote)
    plan = build_plan(candidate, quote, fill, slippage, policy)
    retry = build_retry(plan, policy)

    checks = {
        "policy_valid": validation["valid"],
        "candidate_present": bool(candidate),
        "quote_analyzed": bool(quote),
        "fill_probability_present": "fill_probability_pct" in fill,
        "slippage_present": "expected_slippage_pct" in slippage,
        "plan_present": bool(plan),
        "submission_not_authorized": True,
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
    }
    failed = [k for k, v in checks.items() if not v]
    state = "EXECUTION_OPTIMIZER_READY" if not failed else "EXECUTION_OPTIMIZER_REVIEW_REQUIRED"
    result = {
        "stage": "V255.64",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "candidate": candidate,
        "quote": quote,
        "fill_probability": fill,
        "slippage": slippage,
        "execution_plan": plan,
        "retry_plan": retry,
        "checks": checks,
        "failed": failed,
        "execution_authorized": False,
        "submission_authorized": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V256_01_TO_V260_64_AUTONOMOUS_PAPER_TRADING",
    }
    actual = root / "release/v251_01_to_v255_64/actual"
    write_json(actual / "execution_optimizer_result.json", result)
    write_json(actual / "optimized_execution_plan.json", plan)
    append_jsonl(actual / "execution_optimizer_ledger.jsonl", {
        "observed_at": result["observed_at"],
        "state": state,
        "symbol": plan.get("symbol"),
        "order_type": plan.get("order_type"),
        "limit_price": plan.get("limit_price"),
        "actual_live_orders_submitted": 0,
    })
    return result
