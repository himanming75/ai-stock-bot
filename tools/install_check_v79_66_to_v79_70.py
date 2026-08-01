from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=['alpaca_market_data/historical_indicator_library_v79_66_70.py','tools/run_v79_66_to_v79_70_pipeline.py','tools/test_historical_indicator_library_v79_66_to_v79_70.py','tools/verify_v79_66_to_v79_70_pipeline.py','release/v79_66/config/historical_indicator_config_v79_66.json']
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit('MISSING: '+', '.join(m))
importlib.import_module('alpaca_market_data.historical_indicator_library_v79_66_70').IndicatorConfig().validate()
print('V79.66-V79.70 INSTALL CHECK PASS')
