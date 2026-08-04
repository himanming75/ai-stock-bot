from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from operations_manager.jobs import run
p=argparse.ArgumentParser();p.add_argument("job");a=p.parse_args()
r=run(ROOT,a.job);print(json.dumps(r,indent=2,sort_keys=True))
raise SystemExit(0 if r.get("ok") else 1)
