from pathlib import Path
import importlib, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
REQUIRED=[
 "alpaca_market_data/dataset_versioning_v79_41_45.py",
 "tools/run_v79_41_to_v79_45_pipeline.py",
 "tools/test_dataset_versioning_v79_41_to_v79_45.py",
 "tools/verify_v79_41_to_v79_45_pipeline.py",
 "release/v79_41/config/dataset_version_config_v79_41.json",
]
missing=[p for p in REQUIRED if not (ROOT/p).is_file()]
if missing: raise SystemExit("MISSING: "+", ".join(missing))
module=importlib.import_module("alpaca_market_data.dataset_versioning_v79_41_45")
module.DatasetVersionConfig().validate()
print("V79.41-V79.45 INSTALL CHECK PASS")
