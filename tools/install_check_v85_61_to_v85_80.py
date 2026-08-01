from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_order_submission_sim_v85_61_80.py","tools/run_v85_61_to_v85_80_pipeline.py","tools/test_paper_order_submission_sim_v85_61_to_v85_80.py","tools/verify_v85_61_to_v85_80_pipeline.py","release/v85_61/config/paper_order_submission_sim_config_v85_61.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_order_submission_sim_v85_61_80").PaperOrderSubmissionSimulationConfig().validate()
print("V85.61-V85.80 INSTALL CHECK PASS")
