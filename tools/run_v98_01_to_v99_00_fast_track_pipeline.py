from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.multi_session_validation_fast_track_v98_01_v99_00 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v99_00/output"
if a.clean and out.exists():shutil.rmtree(out)
c=MultiSessionConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V98.01-V99.00","status":cert["status"],
"release_candidate":cert["release_candidate"],**cert["summary"],
"multi_session_validation_fast_track_complete":cert["multi_session_validation_fast_track_complete"],
"actual_paper_multi_session_validation_rc3_ready":cert["actual_paper_multi_session_validation_rc3_ready"],
"session_queue_verified":cert["session_queue_verified"],
"session_isolation_verified":cert["session_isolation_verified"],
"sequential_activation_verified":cert["sequential_activation_verified"],
"concurrent_session_guard_verified":cert["concurrent_session_guard_verified"],
"token_rotation_verified":cert["token_rotation_verified"],
"expiration_cleanup_verified":cert["expiration_cleanup_verified"],
"recovery_matrix_verified":cert["recovery_matrix_verified"],
"audit_chain_verified":cert["audit_chain_verified"],"rollback_verified":cert["rollback_verified"],
"default_network_requests_executed":0,"default_actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
