from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_broker_network_foundation_v85_01_20.py","tools/run_v85_01_to_v85_20_pipeline.py","tools/test_paper_broker_network_foundation_v85_01_to_v85_20.py","tools/verify_v85_01_to_v85_20_pipeline.py","release/v85_01/config/paper_broker_network_foundation_config_v85_01.json"]
m=[x for x in req if not (R/x).is_file()]
if m: raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_broker_network_foundation_v85_01_20").PaperBrokerNetworkFoundationConfig().validate()
print("V85.01-V85.20 INSTALL CHECK PASS")
