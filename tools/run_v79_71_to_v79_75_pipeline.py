from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.historical_signal_engine_v79_71_75 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v79_75/output"
 if a.clean and out.exists():shutil.rmtree(out)
 prior=root/"release/v79_70/output";c=SignalConfig()
 r=run_signal_engine(prior,prior/"historical_indicator_library_certificate_v79_70.json",c,out)
 cert=build_signal_certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V79.71-V79.75","status":cert["status"],**cert["signal_summary"],"network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0,"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
