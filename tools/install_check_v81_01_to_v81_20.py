from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/portfolio_optimization_v81_01_20.py","tools/run_v81_01_to_v81_20_pipeline.py","tools/test_portfolio_optimization_v81_01_to_v81_20.py","tools/verify_v81_01_to_v81_20_pipeline.py","release/v81_01/config/portfolio_optimization_config_v81_01.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.portfolio_optimization_v81_01_20").PortfolioOptimizationConfig().validate()
print("V81.01-V81.20 INSTALL CHECK PASS")
