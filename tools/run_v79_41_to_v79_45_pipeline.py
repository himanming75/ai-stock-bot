from pathlib import Path
import argparse, json, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from alpaca_market_data import (
    DatasetVersionConfig, run_dataset_versioning, build_version_certificate,
)

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--repository-root",default=".")
    parser.add_argument("--clean",action="store_true")
    args=parser.parse_args()
    root=Path(args.repository_root).resolve()
    output=root/"release/v79_45/output"
    if args.clean and output.exists(): shutil.rmtree(output)
    dataset=root/"release/v79_40/output/quality/alpaca_historical_bars.quality_snapshot.jsonl"
    quality_cert=root/"release/v79_40/output/historical_quality_certificate_v79_40.json"
    config=DatasetVersionConfig()
    result=run_dataset_versioning(dataset,quality_cert,config,output)
    cert=build_version_certificate(root,output,config,result)
    print(json.dumps({
        "stage_range":"V79.41-V79.45",
        "status":cert["status"],
        "passed_stage_count":cert["passed_stage_count"],
        "failed_stage_count":cert["failed_stage_count"],
        **cert["version_summary"],
        "network_requests_executed":cert["network_requests_executed"],
        "credentials_used":cert["credentials_used"],
        "trading_client_created":cert["trading_client_created"],
        "actual_orders_submitted":cert["actual_orders_submitted"],
        "next_phase":cert["next_phase"],
    },indent=2,sort_keys=True))
    return 0 if cert["status"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
