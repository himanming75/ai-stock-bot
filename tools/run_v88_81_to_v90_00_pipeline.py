from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path: sys.path.insert(0,str(R))
from alpaca_market_data.fast_track_v88_81_v90_00 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v90_00/output"
if a.clean and out.exists(): shutil.rmtree(out)
c=FastTrackConfig();r=run_engine(root,c,out);cert=certificate(out,c,r)
print(json.dumps({"stage_range":"V88.81-V90.00","status":cert["status"],
"release_candidate":cert["release_candidate"],**cert["summary"],
"paper_automation_framework_certified":cert["paper_automation_framework_certified"],
"portfolio_runtime_foundation_complete":cert["portfolio_runtime_foundation_complete"],
"runtime_risk_engine_complete":cert["runtime_risk_engine_complete"],
"paper_runtime_rc1_ready":cert["paper_runtime_rc1_ready"],
"scheduler_enabled":False,"runtime_loop_enabled":False,"market_data_network_enabled":False,
"paper_order_submission_authorized":False,"network_requests_executed":0,
"actual_orders_submitted":0,"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
