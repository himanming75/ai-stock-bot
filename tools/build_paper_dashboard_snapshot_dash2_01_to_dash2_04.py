from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from dashboard.paper_trading_integration import build_paper_trading_payload
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();root=Path(a.repository_root).resolve()
 out=build_paper_trading_payload(root)
 path=root/"release/dash2_01_to_dash2_04/actual/paper_dashboard_snapshot.json"
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(out,indent=2,sort_keys=True));print("PAPER_DASHBOARD_SNAPSHOT="+str(path));return 0
if __name__=="__main__":raise SystemExit(main())
