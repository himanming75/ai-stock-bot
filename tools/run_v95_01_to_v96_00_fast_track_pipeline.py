from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.controlled_execution_fast_track_v95_01_v96_00 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v96_00/output"
if a.clean and out.exists():shutil.rmtree(out)
c=ControlledExecutionConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V95.01-V96.00","status":cert["status"],
"release_candidate":cert["release_candidate"],**cert["summary"],
"controlled_execution_fast_track_complete":cert["controlled_execution_fast_track_complete"],
"actual_paper_single_order_controlled_rc1_ready":cert["actual_paper_single_order_controlled_rc1_ready"],
"preflight_verified":cert["preflight_verified"],"approval_token_verified":cert["approval_token_verified"],
"fixture_execution_verified":cert["fixture_execution_verified"],
"reconciliation_verified":cert["reconciliation_verified"],
"failure_policy_verified":cert["failure_policy_verified"],
"kill_switch_verified":cert["kill_switch_verified"],"rollback_verified":cert["rollback_verified"],
"real_transport_isolated":cert["real_transport_isolated"],
"default_paper_order_submission_authorized":False,
"default_network_requests_executed":0,"default_actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
