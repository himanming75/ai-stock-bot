from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_session_engine_v80_06_20.py","tools/run_v80_06_to_v80_20_pipeline.py","tools/test_paper_session_engine_v80_06_to_v80_20.py","tools/verify_v80_06_to_v80_20_pipeline.py","release/v80_06/config/paper_session_config_v80_06.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_session_engine_v80_06_20").PaperSessionConfig().validate()
print("V80.06-V80.20 INSTALL CHECK PASS")
