from pathlib import Path
import importlib, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
REQUIRED=[
 "alpaca_market_data/quality_reconciliation_v79_36_40.py",
 "tools/run_v79_36_to_v79_40_pipeline.py",
 "tools/test_quality_reconciliation_v79_36_to_v79_40.py",
 "tools/verify_v79_36_to_v79_40_pipeline.py",
 "release/v79_36/config/quality_config_v79_36.json",
]
missing=[p for p in REQUIRED if not (ROOT/p).is_file()]
if missing: raise SystemExit("MISSING: "+", ".join(missing))
module=importlib.import_module("alpaca_market_data.quality_reconciliation_v79_36_40")
module.QualityConfig().validate()
print("V79.36-V79.40 INSTALL CHECK PASS")
