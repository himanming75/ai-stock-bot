from pathlib import Path
import argparse, json, shutil, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from alpaca_market_data.historical_walk_forward_validation_v79_91_95 import (
    WalkForwardConfig, run_walk_forward_validation,
    build_walk_forward_certificate,
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    output = root / "release/v79_95/output"
    if args.clean and output.exists():
        shutil.rmtree(output)
    portfolio_output = root / "release/v79_80/output"
    performance_output = root / "release/v79_90/output"
    config = WalkForwardConfig()
    result = run_walk_forward_validation(
        portfolio_output,
        portfolio_output / "historical_portfolio_simulation_certificate_v79_80.json",
        performance_output / "historical_performance_analytics_certificate_v79_90.json",
        config,
        output,
    )
    certificate = build_walk_forward_certificate(
        root, output, config, result
    )
    print(json.dumps({
        "stage_range": "V79.91-V79.95",
        "status": certificate["status"],
        **certificate["walk_forward_summary"],
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "next_phase": certificate["next_phase"],
    }, indent=2, sort_keys=True))
    return 0 if certificate["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
