from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.paper_broker_enablement_v82_81_v83_00 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v83_00/output"
 if a.clean and out.exists():shutil.rmtree(out)
 c=PaperBrokerEnablementConfig();r=run_engine(root,c,out);cert=build_certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V82.81-V83.00","status":cert["status"],**cert["paper_broker_summary"],
 "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0,
 "paper_session_authorized":cert["paper_session_authorized"],"paper_trading_authorized":False,
 "live_trading_authorized":False,"paper_broker_enablement_complete":cert["paper_broker_enablement_complete"],
 "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
