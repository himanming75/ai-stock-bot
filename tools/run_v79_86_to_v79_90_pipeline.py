from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.historical_performance_analytics_v79_86_90 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v79_90/output"
 if a.clean and out.exists():shutil.rmtree(out)
 po=root/"release/v79_80/output";ro=root/"release/v79_85/output";c=PerformanceConfig()
 r=run_performance_analytics(po,po/"historical_portfolio_simulation_certificate_v79_80.json",ro/"historical_risk_engine_certificate_v79_85.json",c,out)
 cert=build_performance_certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V79.86-V79.90","status":cert["status"],**cert["performance_summary"],"network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0,"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
