from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/paper_broker_read_only_v85_21_40.py","tools/run_v85_21_to_v85_40_pipeline.py","tools/test_paper_broker_read_only_v85_21_to_v85_40.py","tools/verify_v85_21_to_v85_40_pipeline.py","release/v85_21/config/paper_broker_read_only_config_v85_21.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.paper_broker_read_only_v85_21_40").ReadOnlyConnectionConfig().validate()
print("V85.21-V85.40 INSTALL CHECK PASS")
