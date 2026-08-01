from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_performance_analytics_v81_81_v82_00.py","tools/run_v81_81_to_v82_00_pipeline.py","tools/test_paper_performance_analytics_v81_81_to_v82_00.py","tools/verify_v81_81_to_v82_00_pipeline.py","release/v81_81/config/paper_performance_config_v81_81.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_performance_analytics_v81_81_v82_00").PaperPerformanceConfig().validate()
print("V81.81-V82.00 INSTALL CHECK PASS")
