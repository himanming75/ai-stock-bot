from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/historical_performance_analytics_v79_86_90.py","tools/run_v79_86_to_v79_90_pipeline.py","tools/test_historical_performance_analytics_v79_86_to_v79_90.py","tools/verify_v79_86_to_v79_90_pipeline.py","release/v79_86/config/historical_performance_config_v79_86.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.historical_performance_analytics_v79_86_90").PerformanceConfig().validate()
print("V79.86-V79.90 INSTALL CHECK PASS")
