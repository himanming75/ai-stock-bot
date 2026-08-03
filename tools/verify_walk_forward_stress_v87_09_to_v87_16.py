import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = (
        root / "release/v87_09_to_v87_16/actual/"
        "walk_forward_stress_validation_result.json"
    )
    if not path.exists():
        print(f"RESULT NOT FOUND: {path}")
        return 1

    result = json.loads(path.read_text(encoding="utf-8"))
    validation = result.get("validation", {})
    checks = {
        "stage_range": result.get("stage_range") == "V87.09-V87.16",
        "status_pass": result.get("status") == "PASS",
        "allowed_state": result.get("state") in {
            "BACKTEST_ROBUSTNESS_VALIDATED",
            "BACKTEST_ROBUSTNESS_REVIEW_REQUIRED",
        },
        "walk_forward_windows": (
            validation.get("walk_forward", {}).get("window_count", 0) >= 2
        ),
        "stress_scenarios": (
            validation.get("stress", {}).get("scenario_count", 0) == 5
        ),
        "monte_carlo_iterations": (
            validation.get("monte_carlo", {}).get("iterations", 0) >= 100
        ),
        "overfit_score_valid": (
            0 <= validation.get("overfit", {}).get("overfit_risk_score", -1) <= 100
        ),
        "certificate_hash": (
            len(validation.get("certificate", {}).get("certificate_sha256", ""))
            == 64
        ),
        "paper_only": result.get("paper_only") is True,
        "broker_write_disabled": result.get("broker_write_enabled") is False,
        "order_submission_disabled": result.get("order_submission_enabled") is False,
        "live_trading_disabled": result.get("live_trading_enabled") is False,
        "external_network_disabled": result.get("external_network_enabled") is False,
        "network_requests_zero": result.get("network_requests_executed") == 0,
        "write_requests_zero": result.get("write_requests_executed") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "verification_stage": "V87.16",
        "verification_status": "PASS" if not failed else "FAIL",
        "state": result.get("state"),
        "robustness_passed": validation.get("robustness_passed"),
        "walk_forward_windows": validation.get("walk_forward", {}).get("window_count"),
        "positive_window_pct": validation.get("walk_forward", {}).get("positive_window_pct"),
        "worst_stress_return_pct": validation.get("stress", {}).get("worst_return_pct"),
        "overfit_risk_score": validation.get("overfit", {}).get("overfit_risk_score"),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
