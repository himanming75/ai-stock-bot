from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_order_gate_v83_01_20.py","tools/run_v83_01_to_v83_20_pipeline.py","tools/test_paper_order_gate_v83_01_to_v83_20.py","tools/verify_v83_01_to_v83_20_pipeline.py","release/v83_01/config/paper_order_gate_config_v83_01.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_order_gate_v83_01_20").PaperBrokerOrderGateConfig().validate()
print("V83.01-V83.20 INSTALL CHECK PASS")
