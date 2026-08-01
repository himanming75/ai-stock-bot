from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_order_authorization_v85_41_60.py","tools/run_v85_41_to_v85_60_pipeline.py","tools/test_paper_order_authorization_v85_41_to_v85_60.py","tools/verify_v85_41_to_v85_60_pipeline.py","release/v85_41/config/paper_order_authorization_config_v85_41.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_order_authorization_v85_41_60").PaperOrderAuthorizationConfig().validate()
print("V85.41-V85.60 INSTALL CHECK PASS")
