from pathlib import Path
import argparse, json, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from alpaca_market_data import (
    NetworkSmokeConfig, inspect_network_smoke_preflight,
    execute_historical_network_smoke, sanitize_smoke_result,
    build_network_smoke_certificate,
)
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repository-root",default=".")
    ap.add_argument("--clean",action="store_true")
    args=ap.parse_args()
    root=Path(args.repository_root).resolve()
    out=root/"release/v79_20/output"
    if args.clean and out.exists(): shutil.rmtree(out)
    # Default certification intentionally uses an empty environment.
    source={}
    config=NetworkSmokeConfig()
    preflight=inspect_network_smoke_preflight(source)
    result=execute_historical_network_smoke(source,config)
    sanitized=sanitize_smoke_result(result)
    cert=build_network_smoke_certificate(root,out,config,preflight,result,sanitized)
    print(json.dumps({
      "stage_range":"V79.16-V79.20","status":cert["status"],
      "passed_stage_count":cert["passed_stage_count"],
      "failed_stage_count":cert["failed_stage_count"],
      "network_smoke_mode":cert["network_smoke_mode"],
      "network_requests_executed":cert["network_requests_executed"],
      "credential_use_count":cert["credential_use_count"],
      "credentials_exposed":cert["credentials_exposed"],
      "trading_client_created":cert["trading_client_created"],
      "actual_orders_submitted":cert["actual_orders_submitted"],
      "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
    return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
