from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.controlled_execution_validation_fast_track_v96_01_v97_00 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v97_00/output"
if a.clean and out.exists():shutil.rmtree(out)
c=ValidationConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V96.01-V97.00","status":cert["status"],
"release_candidate":cert["release_candidate"],**cert["summary"],
"controlled_execution_validation_fast_track_complete":cert["controlled_execution_validation_fast_track_complete"],
"actual_paper_controlled_execution_validation_rc1_ready":cert["actual_paper_controlled_execution_validation_rc1_ready"],
"account_validation_verified":cert["account_validation_verified"],
"clock_validation_verified":cert["clock_validation_verified"],
"order_lookup_verified":cert["order_lookup_verified"],
"client_order_id_reconciliation_verified":cert["client_order_id_reconciliation_verified"],
"duplicate_guard_verified":cert["duplicate_guard_verified"],
"unknown_state_recovery_verified":cert["unknown_state_recovery_verified"],
"cancel_policy_verified":cert["cancel_policy_verified"],"rollback_verified":cert["rollback_verified"],
"default_network_requests_executed":0,"default_actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
