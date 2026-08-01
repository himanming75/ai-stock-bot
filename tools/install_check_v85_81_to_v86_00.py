from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_network_enablement_v85_81_v86_00.py","tools/run_v85_81_to_v86_00_pipeline.py","tools/test_paper_network_enablement_v85_81_to_v86_00.py","tools/verify_v85_81_to_v86_00_pipeline.py","release/v85_81/config/paper_network_enablement_config_v85_81.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_network_enablement_v85_81_v86_00").PaperBrokerNetworkEnablementConfig().validate()
print("V85.81-V86.00 INSTALL CHECK PASS")
