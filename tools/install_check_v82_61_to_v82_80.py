from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/dry_run_broker_validation_v82_61_80.py","tools/run_v82_61_to_v82_80_pipeline.py","tools/test_dry_run_broker_validation_v82_61_to_v82_80.py","tools/verify_v82_61_to_v82_80_pipeline.py","release/v82_61/config/dry_run_broker_config_v82_61.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.dry_run_broker_validation_v82_61_80").DryRunBrokerConfig().validate()
print("V82.61-V82.80 INSTALL CHECK PASS")
