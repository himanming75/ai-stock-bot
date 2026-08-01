from pathlib import Path
import argparse,json,shutil,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.paper_session_engine_v80_06_20 import *
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");p.add_argument("--clean",action="store_true");a=p.parse_args()
 root=Path(a.repository_root).resolve();out=root/"release/v80_20/output"
 if a.clean and out.exists():shutil.rmtree(out)
 c=PaperSessionConfig();r=run_paper_session(root,c,out);cert=build_session_certificate(root,out,c,r);s=cert["session_summary"]
 print(json.dumps({"stage_range":"V80.06-V80.20","status":cert["status"],**s,"network_requests_executed":0,"credentials_used":0,"trading_client_created":False,"actual_orders_submitted":0,"paper_trading_authorized":False,"live_trading_authorized":False,"next_phase":cert["next_phase"]},indent=2,sort_keys=True))
 return 0 if cert["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
