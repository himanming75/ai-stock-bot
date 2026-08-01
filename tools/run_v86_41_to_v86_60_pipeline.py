from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.position_account_reconciliation_v86_41_60 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");p.add_argument("--enable-network",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v86_60/output"
 if a.clean and out.exists():shutil.rmtree(out)
 c=PositionAccountReconciliationConfig(explicit_network_opt_in=a.enable_network)
 r=run_engine(root,c,out,enable_network=a.enable_network);cert=certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V86.41-V86.60","status":cert["status"],**cert["position_account_summary"],
 "paper_position_account_reconciliation_complete":cert["paper_position_account_reconciliation_complete"],
 "paper_order_submission_authorized":False,"live_trading_authorized":False,
 "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
