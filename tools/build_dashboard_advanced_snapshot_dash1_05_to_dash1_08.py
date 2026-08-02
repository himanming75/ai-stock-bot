from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from dashboard.advanced_monitoring import build_advanced_payload
def main():
 p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args();root=Path(a.repository_root).resolve()
 out=build_advanced_payload(root)
 path=root/"release/dash1_05_to_dash1_08/actual/dashboard_advanced_snapshot.json"
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(out,indent=2,sort_keys=True));print("ADVANCED_SNAPSHOT="+str(path));return 0
if __name__=="__main__":raise SystemExit(main())
