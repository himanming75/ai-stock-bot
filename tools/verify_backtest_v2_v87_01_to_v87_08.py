import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    path = (
        root / "release/v87_01_to_v87_08/actual/"
        "backtest_v2_result.json"
    )
    if not path.exists():
        print(f"RESULT NOT FOUND: {path}")
        return 1

    result = json.loads(path.read_text(encoding="utf-8"))
    backtest = result.get("backtest", {})
    stats = backtest.get("trade_statistics", {})
    checks = {
        "stage_range": result.get("stage_range") == "V87.01-V87.08",
        "status_pass": result.get("status") == "PASS",
        "state_ready": result.get("state") == "BACKTEST_ENGINE_V2_READY",
        "bars_available": int(backtest.get("bar_count", 0)) >= 50,
        "trades_available": int(stats.get("total_trades", 0)) >= 1,
        "equity_curve_available": len(backtest.get("equity_curve", [])) >= 50,
        "drawdown_curve_available": (
            len(backtest.get("drawdown_curve_pct", []))
            == len(backtest.get("equity_curve", []))
        ),
        "ending_equity_positive": float(backtest.get("ending_equity", 0)) > 0,
        "max_drawdown_valid": (
            float(backtest.get("maximum_drawdown_pct", -1)) >= 0
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
        "verification_stage": "V87.08",
        "verification_status": "PASS" if not failed else "FAIL",
        "symbol": backtest.get("symbol"),
        "total_return_pct": backtest.get("total_return_pct"),
        "maximum_drawdown_pct": backtest.get("maximum_drawdown_pct"),
        "sharpe_ratio": backtest.get("sharpe_ratio"),
        "total_trades": stats.get("total_trades"),
        "win_rate_pct": stats.get("win_rate_pct"),
        "profit_factor": stats.get("profit_factor"),
        "checks": checks,
        "failed": failed,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
