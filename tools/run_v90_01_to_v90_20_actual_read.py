from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
from alpaca_market_data.actual_paper_automation_v90_01_20 import *
c=ActualPaperAutomationConfig()
try:
 r=actual_read_scenario(c)
 print(json.dumps(r,indent=2,sort_keys=True))
 raise SystemExit(0 if r["status"]=="PASS" else 1)
except Exception as e:
 print(json.dumps({"status":"FAIL","error":type(e).__name__,"message":str(e),
 "actual_orders_submitted":0},indent=2,sort_keys=True))
 raise SystemExit(1)
