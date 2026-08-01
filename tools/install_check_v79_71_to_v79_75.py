from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/historical_signal_engine_v79_71_75.py","tools/run_v79_71_to_v79_75_pipeline.py","tools/test_historical_signal_engine_v79_71_to_v79_75.py","tools/verify_v79_71_to_v79_75_pipeline.py","release/v79_71/config/historical_signal_config_v79_71.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.historical_signal_engine_v79_71_75").SignalConfig().validate()
print("V79.71-V79.75 INSTALL CHECK PASS")
