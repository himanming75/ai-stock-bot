from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_automation_optin_v91_01_20 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v91_20/output"
if a.clean and out.exists():shutil.rmtree(out)
c=ActualPaperAutomationOptInConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V91.01-V91.20","status":cert["status"],**cert["summary"],
"actual_paper_automation_opt_in_foundation_complete":cert["actual_paper_automation_opt_in_foundation_complete"],
"read_only_automation_session_ready":cert["read_only_automation_session_ready"],
"multi_approval_verified":cert["multi_approval_verified"],"session_ttl_verified":cert["session_ttl_verified"],
"single_use_token_verified":cert["single_use_token_verified"],"kill_switch_verified":cert["kill_switch_verified"],
"revocation_verified":cert["revocation_verified"],"scheduler_enabled":False,"runtime_loop_enabled":False,
"paper_order_submission_authorized":False,"write_capability_count":0,"actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
