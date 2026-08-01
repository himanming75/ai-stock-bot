from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/strategy_engine_foundation_v80_61_80.py","tools/run_v80_61_to_v80_80_pipeline.py","tools/test_strategy_engine_foundation_v80_61_to_v80_80.py","tools/verify_v80_61_to_v80_80_pipeline.py","release/v80_61/config/strategy_engine_config_v80_61.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.strategy_engine_foundation_v80_61_80").StrategyEngineConfig().validate()
print("V80.61-V80.80 INSTALL CHECK PASS")
