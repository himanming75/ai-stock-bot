from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from production_scheduler.engine import evaluate
from production_scheduler.jobs import run
p=argparse.ArgumentParser();p.add_argument("--job");a=p.parse_args()
r=run(ROOT,a.job) if a.job else evaluate(ROOT)
print(json.dumps(r,indent=2,sort_keys=True))
raise SystemExit(0 if r.get("ok",True) else 1)
