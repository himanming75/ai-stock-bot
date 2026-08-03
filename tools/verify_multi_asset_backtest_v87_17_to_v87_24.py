import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = (
        root / "release/v87_17_to_v87_24/actual/"
        "multi_asset_backtest_result.json"
    )
    if not path.exists():
        print(f"RESULT NOT FOUND: {path}")
        return 1

    result = json.loads(path.read_text(encoding="utf-8"))
    data = result.get("multi_asset", {})
    checks = {
        "stage_range": result.get("stage_range") == "V87.17-V87.24",
        "status_pass": result.get("status") == "PASS",
        "allowed_state": result.get("state") in {
            "MULTI_ASSET_BACKTEST_CERTIFIED",
            "MULTI_ASSET_BACKTEST_REVIEW_REQUIRED",
        },
        "asset_count": data.get("asset_count", 0) >= 3,
        "per_asset_results": len(data.get("per_asset", [])) >= 3,
        "portfolio_equity_curve": len(
            data.get("portfolio", {}).get("equity_curve", [])
        ) >= 50,
        "benchmark_available": (
            float(data.get("benchmark", {}).get("ending_equity", 0)) > 0
        ),
        "sector_performance": len(data.get("sector_performance", {})) >= 2,
        "correlation_matrix": len(data.get("correlation_matrix", {})) >= 3,
        "certificate_hash": (
            len(data.get("certificate", {}).get("certificate_sha256", "")) == 64
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
        "verification_stage": "V87.24",
        "verification_status": "PASS" if not failed else "FAIL",
        "state": result.get("state"),
        "asset_count": data.get("asset_count"),
        "portfolio_return_pct": data.get("portfolio", {}).get("total_return_pct"),
        "benchmark_return_pct": data.get("benchmark", {}).get("total_return_pct"),
        "excess_return_pct": data.get("excess_return_pct"),
        "largest_weight_pct": data.get("concentration", {}).get("largest_weight_pct"),
        "effective_asset_count": data.get("concentration", {}).get("effective_asset_count"),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
