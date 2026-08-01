from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/live_broker_enablement_v84_01_20.py","tools/run_v84_01_to_v84_20_pipeline.py","tools/test_live_broker_enablement_v84_01_to_v84_20.py","tools/verify_v84_01_to_v84_20_pipeline.py","release/v84_01/config/live_broker_enablement_config_v84_01.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.live_broker_enablement_v84_01_20").LiveBrokerEnablementConfig().validate()
print("V84.01-V84.20 INSTALL CHECK PASS")
