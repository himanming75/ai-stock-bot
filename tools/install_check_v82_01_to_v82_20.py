from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/live_safety_foundation_v82_01_20.py","tools/run_v82_01_to_v82_20_pipeline.py","tools/test_live_safety_foundation_v82_01_to_v82_20.py","tools/verify_v82_01_to_v82_20_pipeline.py","release/v82_01/config/live_safety_config_v82_01.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.live_safety_foundation_v82_01_20").LiveSafetyConfig().validate()
print("V82.01-V82.20 INSTALL CHECK PASS")
