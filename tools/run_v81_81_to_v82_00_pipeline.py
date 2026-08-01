from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.paper_performance_analytics_v81_81_v82_00 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v82_00/output"
 if a.clean and out.exists():shutil.rmtree(out)
 c=PaperPerformanceConfig();r=run_engine(root,c,out);cert=build_certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V81.81-V82.00","status":cert["status"],**cert["performance_summary"],
 "network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0,
 "paper_trading_authorized":False,"live_trading_authorized":False,
 "paper_performance_analytics_complete":cert["paper_performance_analytics_complete"],
 "paper_framework_certified":cert["paper_framework_certified"],"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
