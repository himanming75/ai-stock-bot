from pathlib import Path
import argparse, json, shutil, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from alpaca_market_data import (
    QualityConfig, load_quality_dataset, run_quality_reconciliation,
    build_quality_certificate,
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    output = root / "release/v79_40/output"
    quality_dir = output / "quality"
    if args.clean and output.exists(): shutil.rmtree(output)
    dataset = root / "release/v79_35/output/gap_fill/alpaca_historical_bars.gap_filled.jsonl"
    config = QualityConfig()
    rows = load_quality_dataset(dataset)
    result = run_quality_reconciliation(rows, config, quality_dir)
    cert = build_quality_certificate(root, output, config, result)
    print(json.dumps({
        "stage_range": "V79.36-V79.40",
        "status": cert["status"],
        "passed_stage_count": cert["passed_stage_count"],
        "failed_stage_count": cert["failed_stage_count"],
        **cert["quality_summary"],
        "network_requests_executed": cert["network_requests_executed"],
        "credentials_used": cert["credentials_used"],
        "trading_client_created": cert["trading_client_created"],
        "actual_orders_submitted": cert["actual_orders_submitted"],
        "next_phase": cert["next_phase"],
    }, indent=2, sort_keys=True))
    return 0 if cert["status"] == "PASS" else 1

if __name__ == "__main__": raise SystemExit(main())
