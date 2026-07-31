from pathlib import Path
import argparse, json, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from alpaca_market_data import (
    RetentionConfig, run_dataset_retention, build_retention_certificate,
)

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--repository-root",default=".")
    parser.add_argument("--clean",action="store_true")
    args=parser.parse_args()
    root=Path(args.repository_root).resolve()
    output=root/"release/v79_50/output"
    if args.clean and output.exists(): shutil.rmtree(output)
    version_output=root/"release/v79_45/output"
    result=run_dataset_retention(
        version_output/"dataset_version_registry.json",
        version_output/"versions",
        version_output/"historical_dataset_version_certificate_v79_45.json",
        RetentionConfig(),
        output,
    )
    cert=build_retention_certificate(root,output,RetentionConfig(),result)
    print(json.dumps({
        "stage_range":"V79.46-V79.50",
        "status":cert["status"],
        "passed_stage_count":cert["passed_stage_count"],
        "failed_stage_count":cert["failed_stage_count"],
        **cert["retention_summary"],
        "network_requests_executed":cert["network_requests_executed"],
        "credentials_used":cert["credentials_used"],
        "trading_client_created":cert["trading_client_created"],
        "actual_orders_submitted":cert["actual_orders_submitted"],
        "next_phase":cert["next_phase"],
    },indent=2,sort_keys=True))
    return 0 if cert["status"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
