from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/live_order_submission_sim_v84_61_80.py","tools/run_v84_61_to_v84_80_pipeline.py","tools/test_live_order_submission_sim_v84_61_to_v84_80.py","tools/verify_v84_61_to_v84_80_pipeline.py","release/v84_61/config/live_order_submission_sim_config_v84_61.json"]
m=[x for x in req if not (R/x).is_file()]
if m: raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.live_order_submission_sim_v84_61_80").LiveOrderSubmissionSimulationConfig().validate()
print("V84.61-V84.80 INSTALL CHECK PASS")
