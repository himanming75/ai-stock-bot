import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = (
        root / "release/v86_17_to_v86_24/actual/"
        "portfolio_scoring_result.json"
    )
    if not path.exists():
        print(f"RESULT NOT FOUND: {path}")
        return 1

    result = json.loads(path.read_text(encoding="utf-8"))
    portfolio = result.get("portfolio", {})
    summary = portfolio.get("allocation_summary", {})
    checks = {
        "stage_range": result.get("stage_range") == "V86.17-V86.24",
        "status_pass": result.get("status") == "PASS",
        "state_ready": (
            result.get("state") == "PORTFOLIO_SCORING_ENGINE_READY"
        ),
        "ranked_candidates_available": (
            len(portfolio.get("ranked_candidates", [])) >= 1
        ),
        "allocations_available": (
            len(portfolio.get("recommended_allocations", [])) >= 1
        ),
        "exposure_within_limit": (
            float(summary.get("allocated_pct", 0))
            <= float(summary.get("portfolio_exposure_limit_pct", 0))
            + 0.0001
        ),
        "portfolio_score_valid": (
            float(portfolio.get("portfolio_score", -1)) >= 0
        ),
        "diversification_score_valid": (
            0 <= float(portfolio.get("diversification_score", -1)) <= 100
        ),
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
        "verification_stage": "V86.24",
        "verification_status": "PASS" if not failed else "FAIL",
        "portfolio_score": portfolio.get("portfolio_score"),
        "diversification_score": portfolio.get(
            "diversification_score"
        ),
        "allocated_pct": summary.get("allocated_pct"),
        "ranked_count": len(portfolio.get("ranked_candidates", [])),
        "allocation_count": len(
            portfolio.get("recommended_allocations", [])
        ),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
