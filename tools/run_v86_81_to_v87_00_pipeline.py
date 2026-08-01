from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.paper_broker_operations_v86_81_v87_00 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v87_00/output"
 if a.clean and out.exists():shutil.rmtree(out)
 c=PaperBrokerOperationsConfig();r=run_engine(root,c,out);cert=certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V86.81-V87.00","status":cert["status"],**cert["operations_summary"],
 "paper_broker_operations_foundation_complete":cert["paper_broker_operations_foundation_complete"],
 "paper_broker_release_candidate_ready":cert["paper_broker_release_candidate_ready"],
 "paper_order_submission_authorized":False,"live_trading_authorized":False,
 "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
