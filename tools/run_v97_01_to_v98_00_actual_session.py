
from pathlib import Path
import argparse,json,os,sys,time
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.controlled_session_execution_fast_track_v97_01_v98_00 import *

p=argparse.ArgumentParser(description="Start one tightly controlled Alpaca PAPER session.")
p.add_argument("--confirm",required=True)
a=p.parse_args()
if a.confirm!=CONFIRMATION_TEXT:
    raise SystemExit("CONFIRMATION TEXT MISMATCH - SESSION NOT STARTED")
cfg=ControlledSessionConfig()
created=create_session(cfg,int(time.time()))
started=start_session(created,os.environ)
print(json.dumps({"created":created,"started":started},indent=2,sort_keys=True))
raise SystemExit(0 if started["status"]=="ACTIVE" else 1)
