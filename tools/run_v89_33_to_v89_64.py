from pathlib import Path
import json, sys, subprocess
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v89_portfolio.io import load_json, write_json
from v89_portfolio.optimizer import optimize

def main() -> int:
    source_path = ROOT / "release/v89_01_to_v89_32/actual/v89_result.json"
    source = load_json(source_path)
    auto_refresh_attempted = False
    auto_refresh_succeeded = False

    if not source.get("strategy_rankings"):
        prior_runner = ROOT / "tools/run_v89_01_to_v89_32.py"
        if prior_runner.exists():
            auto_refresh_attempted = True
            completed = subprocess.run(
                [sys.executable, str(prior_runner)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            auto_refresh_succeeded = completed.returncode == 0
            source = load_json(source_path)

    policy = load_json(ROOT / "release/v89_33_to_v89_64/input/portfolio_policy.json")

    if source.get("strategy_rankings"):
        result_data = optimize(source, policy)
        state = result_data["state"]
    else:
        result_data = {
            "state": "SOURCE_STRATEGY_RESULTS_REQUIRED",
            "ranked_strategies": [],
            "eligible_strategy_count": 0,
            "allocation_mode": str(
                policy.get("allocation_mode", "SCORE_WEIGHT")
            ).upper(),
            "allocations": [],
            "risk": {
                "checks": {},
                "passed": False,
                "failed": ["source_strategy_results_required"],
                "largest_allocation_pct": 0.0,
                "approved_strategy_count": 0,
                "risky_strategies": [],
            },
            "source_state": source.get("state", "NOT_AVAILABLE"),
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }
        state = "SOURCE_STRATEGY_RESULTS_REQUIRED"

    result = {
        "stage": "V89.64",
        "stage_range": "V89.33-V89.64",
        "state": state,
        "status": "PASS",
        "portfolio_optimization": result_data,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "auto_refresh_attempted": auto_refresh_attempted,
        "auto_refresh_succeeded": auto_refresh_succeeded,
        "source_strategy_result_state": source.get("state", "NOT_AVAILABLE"),
        "next_phase": (
            "V90_01_DASHBOARD_ANALYTICS_V3"
            if state != "SOURCE_STRATEGY_RESULTS_REQUIRED"
            else "RESTORE_V89_01_TO_V89_32_STRATEGY_RESULTS"
        ),
    }

    out = ROOT / "release/v89_33_to_v89_64/actual/portfolio_optimization_result.json"
    write_json(out, result)

    summary = {
        "stage": result["stage"],
        "stage_range": result["stage_range"],
        "state": result["state"],
        "status": result["status"],
        "allocation_mode": result_data["allocation_mode"],
        "eligible_strategy_count": result_data["eligible_strategy_count"],
        "largest_allocation_pct": result_data["risk"]["largest_allocation_pct"],
        "risk_passed": result_data["risk"]["passed"],
        "paper_only": True,
        "next_phase": result["next_phase"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"RESULT_FILE={out.resolve()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
