from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.market_data_operations_v88_41_60 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v88_60/output"
 if a.clean and out.exists():shutil.rmtree(out)
 c=MarketDataOperationsConfig();r=run_engine(root,c,out);cert=certificate(root,out,c,r)
 print(json.dumps({"stage_range":"V88.41-V88.60","status":cert["status"],**cert["market_data_operations_summary"],
 "paper_market_data_operations_foundation_complete":cert["paper_market_data_operations_foundation_complete"],
 "market_data_quality_preview_ready":cert["market_data_quality_preview_ready"],
 "market_data_network_enabled":False,"scheduler_enabled":False,
 "runtime_loop_enabled":False,"auto_execution_enabled":False,
 "paper_order_submission_authorized":False,"live_trading_authorized":False,
 "next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
