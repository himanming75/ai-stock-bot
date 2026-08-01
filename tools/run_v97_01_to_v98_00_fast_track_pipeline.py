from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.controlled_session_execution_fast_track_v97_01_v98_00 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v98_00/output"
if a.clean and out.exists():shutil.rmtree(out)
c=ControlledSessionConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V97.01-V98.00","status":cert["status"],
"release_candidate":cert["release_candidate"],**cert["summary"],
"controlled_session_execution_fast_track_complete":cert["controlled_session_execution_fast_track_complete"],
"actual_paper_controlled_session_rc2_ready":cert["actual_paper_controlled_session_rc2_ready"],
"session_create_verified":cert["session_create_verified"],"session_start_verified":cert["session_start_verified"],
"session_heartbeat_verified":cert["session_heartbeat_verified"],
"duplicate_session_guard_verified":cert["duplicate_session_guard_verified"],
"session_resume_verified":cert["session_resume_verified"],"session_consume_verified":cert["session_consume_verified"],
"session_close_verified":cert["session_close_verified"],"session_recovery_verified":cert["session_recovery_verified"],
"rollback_verified":cert["rollback_verified"],"actual_session_runner_isolated":cert["actual_session_runner_isolated"],
"default_network_requests_executed":0,"default_actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
