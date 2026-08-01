from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.final_paper_automation_certification_v90_81_v91_00 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v91_00/output"
if a.clean and out.exists():shutil.rmtree(out)
c=FinalPaperAutomationCertificationConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V90.81-V91.00","status":cert["status"],"release_candidate":cert["release_candidate"],**cert["summary"],
"final_paper_automation_certification_complete":cert["final_paper_automation_certification_complete"],
"paper_automation_final_rc1_ready":cert["paper_automation_final_rc1_ready"],
"end_to_end_contract_verified":cert["end_to_end_contract_verified"],
"safety_matrix_verified":cert["safety_matrix_verified"],
"deterministic_replay_verified":cert["deterministic_replay_verified"],
"failure_containment_verified":cert["failure_containment_verified"],
"final_rollback_verified":cert["final_rollback_verified"],
"final_release_acceptance_verified":cert["final_release_acceptance_verified"],
"scheduler_enabled":False,"runtime_loop_enabled":False,"write_capability_count":0,
"network_requests_executed":0,"actual_orders_submitted":0,"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
