from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_automation_rc2_certification_v91_61_80 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v91_80/output"
if a.clean and out.exists():shutil.rmtree(out)
c=RC2CertificationConfig();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V91.61-V91.80","status":cert["status"],"release_candidate":cert["release_candidate"],**cert["summary"],
"actual_paper_automation_rc2_certification_complete":cert["actual_paper_automation_rc2_certification_complete"],
"actual_paper_automation_rc2_certified_read_only_ready":cert["actual_paper_automation_rc2_certified_read_only_ready"],
"deterministic_replay_verified":cert["deterministic_replay_verified"],"restart_certified":cert["restart_certified"],
"recovery_certified":cert["recovery_certified"],"tamper_detection_verified":cert["tamper_detection_verified"],
"rollback_certified":cert["rollback_certified"],"release_acceptance_verified":cert["release_acceptance_verified"],
"scheduler_enabled":False,"runtime_loop_enabled":False,"paper_order_submission_authorized":False,
"write_capability_count":0,"network_requests_executed":0,"actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
