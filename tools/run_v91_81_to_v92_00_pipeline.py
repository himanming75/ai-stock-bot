from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_order_submission_optin_v91_81_v92_00 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v92_00/output"
if a.clean and out.exists():shutil.rmtree(out)
c=OrderSubmissionOptInConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V91.81-V92.00","status":cert["status"],**cert["summary"],
"actual_paper_order_submission_opt_in_foundation_complete":cert["actual_paper_order_submission_opt_in_foundation_complete"],
"paper_order_preview_token_ready":cert["paper_order_preview_token_ready"],
"order_intent_validation_verified":cert["order_intent_validation_verified"],
"multi_approval_verified":cert["multi_approval_verified"],"order_token_ttl_verified":cert["order_token_ttl_verified"],
"single_use_order_token_verified":cert["single_use_order_token_verified"],"risk_limits_verified":cert["risk_limits_verified"],
"duplicate_prevention_verified":cert["duplicate_prevention_verified"],"kill_switch_verified":cert["kill_switch_verified"],
"paper_order_submission_authorized":False,"write_capability_count":0,"network_requests_executed":0,
"actual_orders_submitted":0,"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
