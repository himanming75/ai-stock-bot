from pathlib import Path
import argparse, json, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from alpaca_market_data import (
    IncrementalSyncConfig, IngestionConfig, normalize_ingestion_rows,
    load_existing_dataset, run_incremental_sync, build_incremental_sync_certificate,
)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repository-root",default=".")
    ap.add_argument("--clean",action="store_true")
    args=ap.parse_args()
    root=Path(args.repository_root).resolve()
    output=root/"release/v79_30/output"
    sync_dir=output/"sync"
    if args.clean and output.exists(): shutil.rmtree(output)

    existing_path=root/"release/v79_25/output/dataset/alpaca_historical_bars.jsonl"
    existing=load_existing_dataset(existing_path)
    incoming_doc=json.loads((root/"release/v79_27/fixtures/incremental_bars_v79_27.json").read_text(encoding="utf-8"))
    incoming=normalize_ingestion_rows(
        incoming_doc["rows"],
        IngestionConfig(expected_symbols=("AAPL","MSFT","SPY"))
    )
    config=IncrementalSyncConfig()
    result=run_incremental_sync(existing,incoming,config,sync_dir)
    cert=build_incremental_sync_certificate(root,output,config,result)
    print(json.dumps({
      "stage_range":"V79.26-V79.30",
      "status":cert["status"],
      "passed_stage_count":cert["passed_stage_count"],
      "failed_stage_count":cert["failed_stage_count"],
      **result["stats"],
      "checkpoint_count":result["checkpoint_count"],
      "gap_task_count":result["gap_task_count"],
      "gap_expected_bar_count":result["gap_expected_bar_count"],
      "network_requests_executed":cert["network_requests_executed"],
      "credentials_used":cert["credentials_used"],
      "trading_client_created":cert["trading_client_created"],
      "actual_orders_submitted":cert["actual_orders_submitted"],
      "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
    return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
