from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.actual_paper_automation_rc2_v91_41_60 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v91_60/output"
if a.clean and out.exists():shutil.rmtree(out)
c=AutomationRC2Config();r=run_engine(root,c,out);cert=build_certificate(out,c,r)
print(json.dumps({"stage_range":"V91.41-V91.60","status":cert["status"],"release_candidate":cert["release_candidate"],**cert["summary"],
"actual_paper_automation_rc2_foundation_complete":cert["actual_paper_automation_rc2_foundation_complete"],
"actual_paper_automation_rc2_read_only_ready":cert["actual_paper_automation_rc2_read_only_ready"],
"session_persistence_verified":cert["session_persistence_verified"],"recovery_chain_verified":cert["recovery_chain_verified"],
"permission_gate_verified":cert["permission_gate_verified"],"kill_switch_verified":cert["kill_switch_verified"],
"rollback_verified":cert["rollback_verified"],"scheduler_enabled":False,"runtime_loop_enabled":False,
"paper_order_submission_authorized":False,"write_capability_count":0,"actual_orders_submitted":0,
"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
