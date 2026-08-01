from pathlib import Path
import argparse, json, shutil, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from alpaca_market_data.historical_backtest_completion_v79_96_v80_00 import (
    BacktestCompletionConfig,
    run_backtest_completion,
    build_backtest_completion_certificate,
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    output = root / "release/v80_00/output"
    if args.clean and output.exists():
        shutil.rmtree(output)
    config = BacktestCompletionConfig()
    result = run_backtest_completion(root, config, output)
    certificate = build_backtest_completion_certificate(
        root, output, config, result
    )
    summary = certificate["completion_summary"]
    print(json.dumps({
        "stage_range": "V79.96-V80.00",
        "status": certificate["status"],
        "package_id": summary["package_id"],
        "certificate_count": summary["certificate_count"],
        "historical_engine_complete": summary["historical_engine_complete"],
        "feature_count": summary["feature_count"],
        "indicator_count": summary["indicator_count"],
        "signal_row_count": summary["signal_row_count"],
        "portfolio_trade_count": summary["portfolio_trade_count"],
        "risk_violation_count": summary["risk_violation_count"],
        "walk_forward_fold_count": summary["walk_forward_fold_count"],
        "walk_forward_leakage_count": summary["walk_forward_leakage_count"],
        "actual_orders_submitted": 0,
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
        "next_phase": certificate["next_phase"],
    }, indent=2, sort_keys=True))
    return 0 if certificate["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
