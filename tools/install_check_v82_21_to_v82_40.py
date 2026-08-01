from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/broker_read_only_v82_21_40.py","tools/run_v82_21_to_v82_40_pipeline.py","tools/test_broker_read_only_v82_21_to_v82_40.py","tools/verify_v82_21_to_v82_40_pipeline.py","release/v82_21/config/broker_read_only_config_v82_21.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.broker_read_only_v82_21_40").BrokerReadOnlyConfig().validate()
print("V82.21-V82.40 INSTALL CHECK PASS")
