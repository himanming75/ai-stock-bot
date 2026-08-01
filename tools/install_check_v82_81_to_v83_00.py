from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_broker_enablement_v82_81_v83_00.py","tools/run_v82_81_to_v83_00_pipeline.py","tools/test_paper_broker_enablement_v82_81_to_v83_00.py","tools/verify_v82_81_to_v83_00_pipeline.py","release/v82_81/config/paper_broker_enablement_config_v82_81.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_broker_enablement_v82_81_v83_00").PaperBrokerEnablementConfig().validate()
print("V82.81-V83.00 INSTALL CHECK PASS")
