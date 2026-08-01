from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_order_authorization_v83_21_40.py","tools/run_v83_21_to_v83_40_pipeline.py","tools/test_paper_order_authorization_v83_21_to_v83_40.py","tools/verify_v83_21_to_v83_40_pipeline.py","release/v83_21/config/paper_order_authorization_config_v83_21.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_order_authorization_v83_21_40").PaperOrderAuthorizationConfig().validate()
print("V83.21-V83.40 INSTALL CHECK PASS")
