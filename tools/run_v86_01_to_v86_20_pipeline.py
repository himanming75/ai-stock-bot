from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.single_order_network_validation_v86_01_20 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");p.add_argument("--enable-network",action="store_true");p.add_argument("--enable-order",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v86_20/output"
 if a.clean and out.exists():shutil.rmtree(out)
 c=SingleOrderNetworkValidationConfig(explicit_network_opt_in=a.enable_network,explicit_order_opt_in=a.enable_order)
 r=run_engine(root,c,out,enable_network=a.enable_network,enable_order=a.enable_order);cert=build_certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V86.01-V86.20","status":cert["status"],**cert["single_order_summary"],
 "broker_connected":cert["broker_connected"],"paper_order_submission_authorized":False,
 "live_trading_authorized":False,"paper_single_order_validation_complete":cert["paper_single_order_validation_complete"],
 "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
