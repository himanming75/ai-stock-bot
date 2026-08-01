from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_release_candidate_v90_61_80 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v90_80/output"
if a.clean and out.exists(): shutil.rmtree(out)
c=ActualPaperReleaseCandidateConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V90.61-V90.80","status":cert["status"],
"source_release_candidate":cert["source_release_candidate"],"release_candidate":cert["release_candidate"],
**cert["summary"],"actual_paper_release_candidate_complete":cert["actual_paper_release_candidate_complete"],
"actual_paper_read_only_operations_rc1_ready":cert["actual_paper_read_only_operations_rc1_ready"],
"operations_checklist_verified":cert["operations_checklist_verified"],"health_gate_verified":cert["health_gate_verified"],
"startup_verified":cert["startup_verified"],"shutdown_verified":cert["shutdown_verified"],
"incident_response_verified":cert["incident_response_verified"],"rollback_verified":cert["rollback_verified"],
"acceptance_verified":cert["acceptance_verified"],"scheduler_enabled":False,"runtime_loop_enabled":False,
"write_capability_count":0,"network_requests_executed":0,"actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
