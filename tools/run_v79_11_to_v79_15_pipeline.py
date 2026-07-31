from datetime import datetime, timezone
from pathlib import Path
import argparse, json, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from alpaca_market_data import (
    AuthenticatedClientPolicy, inspect_credentials, issue_network_approval,
    build_authenticated_client, authorize_historical_request,
    build_authenticated_gate_certificate,
)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repository-root",default="."); ap.add_argument("--clean",action="store_true")
    args=ap.parse_args(); root=Path(args.repository_root).resolve(); out=root/"release/v79_15/output"
    if args.clean and out.exists(): shutil.rmtree(out)
    # Synthetic credentials only. Never use real environment values in certification.
    source={"APCA_API_KEY_ID":"TESTKEY_1234567890","APCA_API_SECRET_KEY":"TESTSECRET_12345678901234567890"}
    inspection=inspect_credentials(source)
    policy=AuthenticatedClientPolicy()
    approval=issue_network_approval(approved=True,ttl_minutes=5,max_requests=1,
        now=datetime(2026,1,1,tzinfo=timezone.utc),token_id="v79-test-token")
    client_result=build_authenticated_client(source,inspection,policy)
    auth=authorize_historical_request(approval,policy,requested_operation="GET_STOCK_BARS",
        now=datetime(2026,1,1,0,1,tzinfo=timezone.utc))
    cert=build_authenticated_gate_certificate(root,out,inspection,approval,policy,client_result.metadata,auth)
    print(json.dumps({
      "stage_range":"V79.11-V79.15","status":cert["status"],
      "passed_stage_count":cert["passed_stage_count"],"failed_stage_count":cert["failed_stage_count"],
      "credential_pair_complete":inspection.pair_complete,
      "client_type":client_result.metadata["client_type"],
      "network_requests_executed":cert["network_requests_executed"],
      "credentials_exposed":cert["credentials_exposed"],
      "trading_client_created":cert["trading_client_created"],
      "actual_orders_submitted":cert["actual_orders_submitted"],
      "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
    return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
