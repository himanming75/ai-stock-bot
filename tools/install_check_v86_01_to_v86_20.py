from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
for x in ["alpaca_market_data/single_order_network_validation_v86_01_20.py","tools/run_v86_01_to_v86_20_pipeline.py","tools/test_single_order_network_validation_v86_01_to_v86_20.py","tools/verify_v86_01_to_v86_20_pipeline.py"]:
 if not (R/x).is_file():raise SystemExit("MISSING: "+x)
importlib.import_module("alpaca_market_data.single_order_network_validation_v86_01_20").SingleOrderNetworkValidationConfig().validate()
print("V86.01-V86.20 INSTALL CHECK PASS")
