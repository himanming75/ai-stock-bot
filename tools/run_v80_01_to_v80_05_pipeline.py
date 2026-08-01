from pathlib import Path
import argparse, json, shutil, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from alpaca_market_data.paper_trading_readiness_v80_01_05 import (
    PaperReadinessConfig,
    run_paper_readiness,
    build_paper_readiness_certificate,
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    root = Path(args.repository_root).resolve()
    output = root / "release/v80_05/output"
    if args.clean and output.exists():
        shutil.rmtree(output)
    config = PaperReadinessConfig()
    result = run_paper_readiness(root, config, output)
    certificate = build_paper_readiness_certificate(
        root, output, config, result
    )
    summary = certificate["readiness_summary"]
    print(json.dumps({
        "stage_range": "V80.01-V80.05",
        "status": certificate["status"],
        "package_id": summary["package_id"],
        "readiness_level": summary["readiness_level"],
        "intent_receipt_count": summary["intent_receipt_count"],
        "forbidden_capability_count": summary[
            "forbidden_capability_count"
        ],
        "network_requests_executed": 0,
        "credentials_used": 0,
        "trading_client_created": False,
        "actual_orders_submitted": 0,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
        "next_phase": certificate["next_phase"],
    }, indent=2, sort_keys=True))
    return 0 if certificate["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
