from pathlib import Path
import argparse, json, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from alpaca_market_data import IngestionConfig, run_historical_ingestion, build_ingestion_certificate
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repository-root",default=".")
    ap.add_argument("--clean",action="store_true")
    args=ap.parse_args()
    root=Path(args.repository_root).resolve()
    output=root/"release/v79_25/output"
    dataset_dir=output/"dataset"
    if args.clean and output.exists(): shutil.rmtree(output)
    raw=json.loads((root/"release/v79_22/fixtures/multi_symbol_historical_bars_v79_22.json").read_text(encoding="utf-8"))["rows"]
    config=IngestionConfig()
    result=run_historical_ingestion(raw,config,dataset_dir)
    cert=build_ingestion_certificate(root,output,config,result)
    print(json.dumps({
      "stage_range":"V79.21-V79.25",
      "status":cert["status"],
      "passed_stage_count":cert["passed_stage_count"],
      "failed_stage_count":cert["failed_stage_count"],
      "normalized_row_count":result["normalized_row_count"],
      "stored_row_count":result["stored_row_count"],
      "duplicate_count_removed":result["duplicate_count_removed"],
      "symbols":result["validation"]["symbols"],
      "network_requests_executed":cert["network_requests_executed"],
      "credentials_used":cert["credentials_used"],
      "trading_client_created":cert["trading_client_created"],
      "actual_orders_submitted":cert["actual_orders_submitted"],
      "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
    return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
