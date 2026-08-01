from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/execution_simulation_v81_61_80.py","tools/run_v81_61_to_v81_80_pipeline.py","tools/test_execution_simulation_v81_61_to_v81_80.py","tools/verify_v81_61_to_v81_80_pipeline.py","release/v81_61/config/execution_simulation_config_v81_61.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.execution_simulation_v81_61_80").ExecutionSimulationConfig().validate()
print("V81.61-V81.80 INSTALL CHECK PASS")
