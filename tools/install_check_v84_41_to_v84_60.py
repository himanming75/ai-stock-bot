from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/live_order_authorization_v84_41_60.py","tools/run_v84_41_to_v84_60_pipeline.py","tools/test_live_order_authorization_v84_41_to_v84_60.py","tools/verify_v84_41_to_v84_60_pipeline.py","release/v84_41/config/live_order_authorization_config_v84_41.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.live_order_authorization_v84_41_60").LiveOrderAuthorizationConfig().validate()
print("V84.41-V84.60 INSTALL CHECK PASS")
