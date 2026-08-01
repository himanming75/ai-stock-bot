
from pathlib import Path
import argparse, json, os, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.controlled_execution_fast_track_v95_01_v96_00 import *

p=argparse.ArgumentParser(description="Submit exactly one Alpaca PAPER order after all explicit gates pass.")
p.add_argument("--symbol",choices=["AAPL","MSFT","SPY"],default="AAPL")
p.add_argument("--side",choices=["buy","sell"],default="buy")
p.add_argument("--estimated-price",type=float,required=True)
p.add_argument("--confirm",required=True)
a=p.parse_args()

if a.confirm != CONFIRMATION_TEXT:
    raise SystemExit("CONFIRMATION TEXT MISMATCH - NO ORDER SUBMITTED")

config=ControlledExecutionConfig(symbol=a.symbol,side=a.side,estimated_price=a.estimated_price)
config.validate()
result=execute_once(config,AlpacaPaperTransport(),os.environ,allow_network=True)
print(json.dumps(result,indent=2,sort_keys=True))
if result["status"]!="SUBMITTED":
    raise SystemExit(1)
