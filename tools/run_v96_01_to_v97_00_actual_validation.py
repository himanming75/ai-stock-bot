
from pathlib import Path
import argparse,json,os,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from alpaca_market_data.controlled_execution_validation_fast_track_v96_01_v97_00 import *

p=argparse.ArgumentParser(description="Read back and validate one existing Alpaca PAPER order.")
p.add_argument("--client-order-id",required=True)
p.add_argument("--symbol",choices=["AAPL","MSFT","SPY"],required=True)
p.add_argument("--side",choices=["buy","sell"],required=True)
p.add_argument("--confirm",required=True)
a=p.parse_args()
if a.confirm!=VALIDATION_CONFIRMATION:
    raise SystemExit("CONFIRMATION TEXT MISMATCH - NO NETWORK REQUEST EXECUTED")
cfg=ValidationConfig(symbol=a.symbol,side=a.side)
result=validate_cycle(cfg,AlpacaPaperReadTransport(),os.environ,allow_network=True,
                      client_order_id=a.client_order_id)
print(json.dumps(result,indent=2,sort_keys=True))
raise SystemExit(0 if result["status"]=="PASS" else 1)
