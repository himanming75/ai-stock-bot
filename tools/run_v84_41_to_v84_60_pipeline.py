from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.live_order_authorization_v84_41_60 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v84_60/output"
 if a.clean and out.exists():shutil.rmtree(out)
 c=LiveOrderAuthorizationConfig();r=run_engine(root,c,out);cert=build_certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V84.41-V84.60","status":cert["status"],**cert["live_order_authorization_summary"],
 "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0,
 "live_order_authorization_ready":cert["live_order_authorization_ready"],
 "live_order_submission_authorized":False,"live_trading_authorized":False,
 "live_order_authorization_foundation_complete":cert["live_order_authorization_foundation_complete"],
 "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
