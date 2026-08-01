from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.live_broker_final_cert_v84_81_v85_00 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v85_00/output"
 if a.clean and out.exists():shutil.rmtree(out)
 c=LiveBrokerFinalCertificationConfig();r=run_engine(root,c,out);cert=build_certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V84.81-V85.00","status":cert["status"],**cert["live_broker_final_summary"],
 "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0,
 "live_order_submission_authorized":False,"live_trading_authorized":False,
 "live_framework_certified":cert["live_framework_certified"],
 "live_broker_framework_complete":cert["live_broker_framework_complete"],
 "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
