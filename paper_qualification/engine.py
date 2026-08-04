from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from paper_qualification.config import load, validate
from paper_qualification.io import load_json, write_json, append_jsonl
from paper_qualification.metrics import calculate
from paper_qualification.order_states import coverage
from paper_qualification.reconciliation import compare
from paper_qualification.recovery import evaluate as evaluate_recovery

def evaluate(root: Path) -> dict:
    policy = load(root)
    validation = validate(policy)
    fixture = load_json(root / "release/v291_01_to_v300_64/input/paper_qualification_fixture.json")
    reconciliation = compare(fixture.get("internal_state", {}), fixture.get("broker_state", {}))
    state_coverage = coverage(fixture.get("order_events", []))
    recovery = evaluate_recovery(fixture.get("recovery_events", []))
    metrics = calculate(fixture.get("trades", []), fixture.get("equity_curve", []))

    sessions = int(fixture.get("sessions_completed", 0) or 0)
    cycles = int(fixture.get("cycles_completed", 0) or 0)
    reconciliation_pass_rate = float(fixture.get("reconciliation_pass_rate_pct", 0) or 0)

    checks = {
        "policy_valid": validation["valid"],
        "paper_endpoint_only": policy.get("paper_base_url") == "https://paper-api.alpaca.markets",
        "sessions_sufficient": sessions >= int(policy["minimum_sessions"]),
        "cycles_sufficient": cycles >= int(policy["minimum_cycles"]),
        "reconciliation_current_pass": reconciliation["passed"],
        "reconciliation_pass_rate": reconciliation_pass_rate >= float(policy["minimum_reconciliation_pass_rate_pct"]),
        "unresolved_mismatches_zero": recovery["unresolved_mismatches"] <= int(policy["maximum_unresolved_mismatches"]),
        "duplicates_zero": recovery["duplicate_orders"] <= int(policy["maximum_duplicate_orders"]),
        "recovery_failures_zero": recovery["recovery_failures"] <= int(policy["maximum_recovery_failures"]),
        "order_state_coverage": state_coverage["coverage_pct"] >= float(policy["minimum_order_state_coverage_pct"]),
        "drawdown_within_limit": metrics["maximum_drawdown_pct"] <= float(policy["maximum_daily_drawdown_pct"]),
        "profit_factor_sufficient": metrics["profit_factor"] >= float(policy["minimum_profit_factor"]),
        "win_rate_sufficient": metrics["win_rate_pct"] >= float(policy["minimum_win_rate_pct"]),
        "paper_submission_disabled": policy.get("paper_submission_enabled") is False,
        "live_submission_disabled": policy.get("live_submission_enabled") is False,
        "live_network_disabled": policy.get("live_network_enabled") is False,
        "broker_write_disabled": policy.get("broker_write_enabled") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    qualification_state = "PAPER_QUALIFIED" if not failed else "PAPER_QUALIFICATION_IN_PROGRESS"
    result = {
        "stage": "V300.64",
        "state": qualification_state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "sessions_completed": sessions,
        "cycles_completed": cycles,
        "reconciliation_pass_rate_pct": reconciliation_pass_rate,
        "reconciliation": reconciliation,
        "order_state_coverage": state_coverage,
        "recovery": recovery,
        "performance_metrics": metrics,
        "checks": checks,
        "failed": failed,
        "paper_read_enabled": policy.get("paper_read_enabled") is True,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "live_network_enabled": False,
        "broker_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_phase": "V301_01_TO_V310_64_RESTRICTED_LIVE_QUALIFICATION",
    }
    actual = root / "release/v291_01_to_v300_64/actual"
    write_json(actual / "paper_qualification_result.json", result)
    write_json(actual / "broker_reconciliation_result.json", reconciliation)
    write_json(actual / "paper_performance_metrics.json", metrics)
    append_jsonl(actual / "paper_qualification_ledger.jsonl", {
        "observed_at": result["observed_at"],
        "state": qualification_state,
        "sessions_completed": sessions,
        "cycles_completed": cycles,
        "failed": failed,
        "actual_live_orders_submitted": 0,
    })
    return result
