from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/historical_portfolio_simulation_v79_76_80.py","tools/run_v79_76_to_v79_80_pipeline.py","tools/test_historical_portfolio_simulation_v79_76_to_v79_80.py","tools/verify_v79_76_to_v79_80_pipeline.py","release/v79_76/config/historical_portfolio_config_v79_76.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.historical_portfolio_simulation_v79_76_80").PortfolioConfig().validate()
print("V79.76-V79.80 INSTALL CHECK PASS")
