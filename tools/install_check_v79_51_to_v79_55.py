from pathlib import Path
import importlib,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
R=["alpaca_market_data/dataset_recovery_v79_51_55.py","tools/run_v79_51_to_v79_55_pipeline.py","tools/test_dataset_recovery_v79_51_to_v79_55.py","tools/verify_v79_51_to_v79_55_pipeline.py","release/v79_51/config/dataset_recovery_config_v79_51.json"]
m=[p for p in R if not (ROOT/p).is_file()]
if m:raise SystemExit("MISSING: "+", ".join(m))
importlib.import_module("alpaca_market_data.dataset_recovery_v79_51_55").RecoveryConfig().validate();print("V79.51-V79.55 INSTALL CHECK PASS")
