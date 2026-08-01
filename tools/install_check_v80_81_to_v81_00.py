from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/strategy_selection_v80_81_v81_00.py","tools/run_v80_81_to_v81_00_pipeline.py","tools/test_strategy_selection_v80_81_to_v81_00.py","tools/verify_v80_81_to_v81_00_pipeline.py","release/v80_81/config/strategy_selection_config_v80_81.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.strategy_selection_v80_81_v81_00").StrategySelectionConfig().validate()
print("V80.81-V81.00 INSTALL CHECK PASS")
