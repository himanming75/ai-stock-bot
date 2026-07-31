from pathlib import Path
import importlib, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
REQUIRED=[
 "alpaca_market_data/dataset_retention_v79_46_50.py",
 "tools/run_v79_46_to_v79_50_pipeline.py",
 "tools/test_dataset_retention_v79_46_to_v79_50.py",
 "tools/verify_v79_46_to_v79_50_pipeline.py",
 "release/v79_46/config/dataset_retention_config_v79_46.json",
]
missing=[p for p in REQUIRED if not (ROOT/p).is_file()]
if missing: raise SystemExit("MISSING: "+", ".join(missing))
module=importlib.import_module("alpaca_market_data.dataset_retention_v79_46_50")
module.RetentionConfig().validate()
print("V79.46-V79.50 INSTALL CHECK PASS")
