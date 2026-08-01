from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
required=["alpaca_market_data/broker_adapter_foundation_v81_41_60.py","tools/run_v81_41_to_v81_60_pipeline.py","tools/test_broker_adapter_foundation_v81_41_to_v81_60.py","tools/verify_v81_41_to_v81_60_pipeline.py","release/v81_41/config/broker_adapter_config_v81_41.json"]
missing=[x for x in required if not (R/x).is_file()]
if missing:raise SystemExit("MISSING: "+", ".join(missing))
importlib.import_module("alpaca_market_data.broker_adapter_foundation_v81_41_60").BrokerAdapterConfig().validate()
print("V81.41-V81.60 INSTALL CHECK PASS")
