from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/live_order_gate_v84_21_40.py","tools/run_v84_21_to_v84_40_pipeline.py","tools/test_live_order_gate_v84_21_to_v84_40.py","tools/verify_v84_21_to_v84_40_pipeline.py","release/v84_21/config/live_order_gate_config_v84_21.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.live_order_gate_v84_21_40").LiveOrderGateConfig().validate()
print("V84.21-V84.40 INSTALL CHECK PASS")
