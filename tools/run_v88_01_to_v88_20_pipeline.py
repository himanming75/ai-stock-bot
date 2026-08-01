from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.paper_scheduler_foundation_v88_01_20 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v88_20/output"
 if a.clean and out.exists():shutil.rmtree(out)
 c=PaperSchedulerFoundationConfig();r=run_engine(root,c,out);cert=certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V88.01-V88.20","status":cert["status"],**cert["scheduler_foundation_summary"],
 "paper_scheduler_foundation_complete":cert["paper_scheduler_foundation_complete"],
 "scheduler_preview_ready":cert["scheduler_preview_ready"],
 "scheduler_enabled":False,"auto_execution_enabled":False,
 "paper_order_submission_authorized":False,"live_trading_authorized":False,
 "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
