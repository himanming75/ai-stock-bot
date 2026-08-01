from pathlib import Path
import argparse,json,shutil,sys,os
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.paper_broker_read_only_v85_21_40 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");p.add_argument("--enable-network",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v85_40/output"
 if a.clean and out.exists():shutil.rmtree(out)
 c=ReadOnlyConnectionConfig(explicit_network_opt_in=a.enable_network)
 r=run_engine(root,c,out,enable_network=a.enable_network);cert=build_certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V85.21-V85.40","status":cert["status"],**cert["paper_read_only_summary"],
 "trading_client_created":False,"actual_orders_submitted":0,"broker_connected":cert["broker_connected"],
 "paper_order_submission_authorized":False,"live_trading_authorized":False,
 "paper_read_only_validation_complete":cert["paper_read_only_validation_complete"],
 "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
