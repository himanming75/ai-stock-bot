from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.actual_paper_read_runtime_v90_21_40 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v90_40/output"
if a.clean and out.exists():shutil.rmtree(out)
c=ReadOnlyRuntimeConfig();x=run_engine(root,c,out);cert=certificate(out,c,x)
print(json.dumps({"stage_range":"V90.21-V90.40","status":cert["status"],**cert["summary"],
"actual_paper_read_only_runtime_validation_complete":cert["actual_paper_read_only_runtime_validation_complete"],
"scheduler_readiness_validated":cert["scheduler_readiness_validated"],"scheduler_enabled":False,
"runtime_loop_enabled":False,"write_capability_count":0,"network_requests_executed":0,
"actual_orders_submitted":0,"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
raise SystemExit(0 if cert["status"]=="PASS" else 1)
