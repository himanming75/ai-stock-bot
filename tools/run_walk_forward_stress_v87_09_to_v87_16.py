from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtest_v2.io import load_json, parse_input
from validation_v2.engine import run_validation
from validation_v2.io import write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(
            ROOT / "release/v87_01_to_v87_08/input/"
            "backtest_sample.json"
        ),
    )
    parser.add_argument(
        "--policy",
        default=str(
            ROOT / "release/v87_09_to_v87_16/input/"
            "walk_forward_stress_policy.json"
        ),
    )
    args = parser.parse_args()

    payload = load_json(Path(args.input))
    symbol, bars, backtest_policy = parse_input(payload)
    policy = load_json(Path(args.policy))
    policy["backtest_policy"] = {
        **backtest_policy,
        **policy.get("backtest_policy", {}),
    }

    validation = run_validation(symbol, bars, policy)
    state = (
        "BACKTEST_ROBUSTNESS_VALIDATED"
        if validation["robustness_passed"]
        else "BACKTEST_ROBUSTNESS_REVIEW_REQUIRED"
    )

    result = {
        "stage": "V87.16",
        "stage_range": "V87.09-V87.16",
        "state": state,
        "status": "PASS",
        "implementation_type": "LOCAL_WALK_FORWARD_STRESS_VALIDATION",
        "validation": validation,
        "paper_only": True,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "broker_command_execution_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "next_phase": "V87_17_MULTI_ASSET_BACKTEST_AND_BENCHMARK",
    }

    actual = ROOT / "release/v87_09_to_v87_16/actual"
    result_path = actual / "walk_forward_stress_validation_result.json"
    write_json(result_path, result)
    write_json(
        actual / "backtest_robustness_certificate.json",
        validation["certificate"],
    )

    summary = {
        "stage": result["stage"],
        "state": result["state"],
        "status": result["status"],
        "walk_forward_windows": validation["walk_forward"]["window_count"],
        "positive_window_pct": validation["walk_forward"]["positive_window_pct"],
        "worst_stress_return_pct": validation["stress"]["worst_return_pct"],
        "worst_stress_drawdown_pct": validation["stress"]["worst_drawdown_pct"],
        "overfit_risk_score": validation["overfit"]["overfit_risk_score"],
        "overfit_risk_level": validation["overfit"]["overfit_risk_level"],
        "monte_carlo_loss_probability_pct": (
            validation["monte_carlo"]["probability_of_loss_pct"]
        ),
        "robustness_passed": validation["robustness_passed"],
        "paper_only": True,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"RESULT_FILE={result_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
