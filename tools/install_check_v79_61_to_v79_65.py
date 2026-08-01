from pathlib import Path
import importlib,sys
R=Path(__file__).resolve().parents[1]
if str(R) not in sys.path:sys.path.insert(0,str(R))
importlib.import_module('alpaca_market_data.historical_feature_store_v79_61_65').FeatureStoreConfig().validate()
print('V79.61-V79.65 INSTALL CHECK PASS')
