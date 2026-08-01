from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from alpaca_market_data.order_lifecycle_v86_21_40 import *
p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");p.add_argument("--enable-network",action="store_true");a=p.parse_args()
root=Path(a.repository_root).resolve();out=root/"release/v86_40/output"
if a.clean and out.exists():shutil.rmtree(out)
c=LifecycleConfig(explicit_network_opt_in=a.enable_network);r=run_engine(root,c,out,enable_network=a.enable_network);cert=certificate(root,out,c,r)
print(json.dumps({"stage_range":"V86.21-V86.40","status":cert["status"],**cert["lifecycle_summary"],"paper_order_lifecycle_validation_complete":cert["paper_order_lifecycle_validation_complete"],"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
