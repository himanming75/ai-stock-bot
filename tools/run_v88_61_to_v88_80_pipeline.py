from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path: sys.path.insert(0,str(R))
from alpaca_market_data.scheduler_runtime_simulation_v88_61_80 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v88_80/output"
if a.clean and out.exists(): shutil.rmtree(out)
c=SchedulerRuntimeSimulationConfig();r=run_engine(root,c,out);cert=certificate(out,c,r)
print(json.dumps({"stage_range":"V88.61-V88.80","status":cert["status"],**cert["summary"],
"scheduler_runtime_simulation_complete":cert["scheduler_runtime_simulation_complete"],
"daily_runtime_simulation_certified":cert["daily_runtime_simulation_certified"],
"scheduler_enabled":False,"runtime_loop_enabled":False,"market_data_network_enabled":False,
"network_requests_executed":0,"actual_orders_submitted":0,"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
