from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
req=["alpaca_market_data/multi_asset_portfolio_v81_21_40.py","tools/run_v81_21_to_v81_40_pipeline.py","tools/test_multi_asset_portfolio_v81_21_to_v81_40.py","tools/verify_v81_21_to_v81_40_pipeline.py","release/v81_21/config/multi_asset_config_v81_21.json"]
m=[x for x in req if not (R/x).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.multi_asset_portfolio_v81_21_40").MultiAssetPortfolioConfig().validate()
print("V81.21-V81.40 INSTALL CHECK PASS")
