from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.single_order_network_optin_fast_track_v94_01_v95_00 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v95_00/output"
if a.clean and out.exists():shutil.rmtree(out)
c=NetworkOptInConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V94.01-V95.00","status":cert["status"],
"release_candidate":cert["release_candidate"],**cert["summary"],
"single_order_network_opt_in_fast_track_complete":cert["single_order_network_opt_in_fast_track_complete"],
"actual_paper_single_order_network_ready_rc1":cert["actual_paper_single_order_network_ready_rc1"],
"credential_loading_verified":cert["credential_loading_verified"],
"paper_url_lock_verified":cert["paper_url_lock_verified"],
"read_network_opt_in_verified":cert["read_network_opt_in_verified"],
"write_contract_verified":cert["write_contract_verified"],
"request_signing_preview_verified":cert["request_signing_preview_verified"],
"response_parser_verified":cert["response_parser_verified"],
"network_failure_policy_verified":cert["network_failure_policy_verified"],
"reconciliation_verified":cert["reconciliation_verified"],
"rollback_verified":cert["rollback_verified"],
"paper_order_submission_authorized":False,"write_capability_count":0,
"network_requests_executed":0,"actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
