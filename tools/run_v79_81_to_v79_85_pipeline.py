from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.historical_risk_engine_v79_81_85 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v79_85/output"
 if a.clean and out.exists():shutil.rmtree(out)
 prior=root/"release/v79_80/output";c=RiskConfig()
 r=run_risk_engine(prior,prior/"historical_portfolio_simulation_certificate_v79_80.json",c,out)
 cert=build_risk_certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V79.81-V79.85","status":cert["status"],**cert["risk_summary"],"network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0,"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
