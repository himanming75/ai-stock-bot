from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_order_submission_sim_v83_41_60.py","tools/run_v83_41_to_v83_60_pipeline.py","tools/test_paper_order_submission_sim_v83_41_to_v83_60.py","tools/verify_v83_41_to_v83_60_pipeline.py","release/v83_41/config/paper_order_submission_sim_config_v83_41.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_order_submission_sim_v83_41_60").PaperOrderSubmissionSimulationConfig().validate()
print("V83.41-V83.60 INSTALL CHECK PASS")
