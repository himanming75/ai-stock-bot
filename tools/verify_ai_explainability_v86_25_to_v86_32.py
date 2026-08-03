import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = (
        root / "release/v86_25_to_v86_32/actual/"
        "ai_explainability_result.json"
    )
    if not path.exists():
        print(f"RESULT NOT FOUND: {path}")
        return 1

    result = json.loads(path.read_text(encoding="utf-8"))
    report = result.get("report", {})
    strategy = report.get("strategy_explanation", {})
    portfolio = report.get("portfolio_explanation", {})

    checks = {
        "stage_range": result.get("stage_range") == "V86.25-V86.32",
        "status_pass": result.get("status") == "PASS",
        "state_ready": (
            result.get("state") == "AI_EXPLAINABILITY_ENGINE_READY"
        ),
        "strategy_narrative": bool(strategy.get("narrative")),
        "strategy_contributions": (
            len(strategy.get("signal_contributions", [])) >= 1
        ),
        "strategy_risks": len(strategy.get("risk_factors", [])) >= 1,
        "portfolio_narrative": bool(portfolio.get("narrative")),
        "portfolio_contributions": (
            len(portfolio.get("allocation_contributions", [])) >= 1
        ),
        "portfolio_comparisons": (
            len(portfolio.get("comparisons", [])) >= 1
        ),
        "limitations_present": len(report.get("limitations", [])) >= 4,
        "paper_only": result.get("paper_only") is True,
        "broker_write_disabled": result.get("broker_write_enabled") is False,
        "order_submission_disabled": (
            result.get("order_submission_enabled") is False
        ),
        "live_trading_disabled": result.get("live_trading_enabled") is False,
        "external_network_disabled": (
            result.get("external_network_enabled") is False
        ),
        "network_requests_zero": result.get("network_requests_executed") == 0,
        "write_requests_zero": result.get("write_requests_executed") == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "verification_stage": "V86.32",
        "verification_status": "PASS" if not failed else "FAIL",
        "strategy_risk_count": len(strategy.get("risk_factors", [])),
        "portfolio_risk_count": len(portfolio.get("risk_factors", [])),
        "comparison_count": len(portfolio.get("comparisons", [])),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
