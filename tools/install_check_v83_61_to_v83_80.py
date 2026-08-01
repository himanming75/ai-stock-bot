from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_broker_execution_sim_v83_61_80.py","tools/run_v83_61_to_v83_80_pipeline.py","tools/test_paper_broker_execution_sim_v83_61_to_v83_80.py","tools/verify_v83_61_to_v83_80_pipeline.py","release/v83_61/config/paper_broker_execution_sim_config_v83_61.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_broker_execution_sim_v83_61_80").PaperBrokerExecutionSimulationConfig().validate()
print("V83.61-V83.80 INSTALL CHECK PASS")
