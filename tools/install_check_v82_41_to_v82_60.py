from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/broker_connection_validation_v82_41_60.py","tools/run_v82_41_to_v82_60_pipeline.py","tools/test_broker_connection_validation_v82_41_to_v82_60.py","tools/verify_v82_41_to_v82_60_pipeline.py","release/v82_41/config/broker_connection_validation_config_v82_41.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.broker_connection_validation_v82_41_60").BrokerConnectionValidationConfig().validate()
print("V82.41-V82.60 INSTALL CHECK PASS")
