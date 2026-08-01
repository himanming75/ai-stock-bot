from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/historical_risk_engine_v79_81_85.py","tools/run_v79_81_to_v79_85_pipeline.py","tools/test_historical_risk_engine_v79_81_to_v79_85.py","tools/verify_v79_81_to_v79_85_pipeline.py","release/v79_81/config/historical_risk_config_v79_81.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.historical_risk_engine_v79_81_85").RiskConfig().validate()
print("V79.81-V79.85 INSTALL CHECK PASS")
