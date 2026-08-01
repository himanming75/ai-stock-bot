from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_monitoring_completion_v80_41_60.py","tools/run_v80_41_to_v80_60_pipeline.py","tools/test_paper_monitoring_completion_v80_41_to_v80_60.py","tools/verify_v80_41_to_v80_60_pipeline.py","release/v80_41/config/paper_monitoring_config_v80_41.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_monitoring_completion_v80_41_60").PaperMonitoringConfig().validate()
print("V80.41-V80.60 INSTALL CHECK PASS")
