from pathlib import Path
import importlib, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
required = [
    "alpaca_market_data/historical_walk_forward_validation_v79_91_95.py",
    "tools/run_v79_91_to_v79_95_pipeline.py",
    "tools/test_historical_walk_forward_validation_v79_91_to_v79_95.py",
    "tools/verify_v79_91_to_v79_95_pipeline.py",
    "release/v79_91/config/historical_walk_forward_config_v79_91.json",
]
missing = [path for path in required if not (ROOT / path).is_file()]
if missing:
    raise SystemExit("MISSING: " + ", ".join(missing))
module = importlib.import_module(
    "alpaca_market_data.historical_walk_forward_validation_v79_91_95"
)
module.WalkForwardConfig().validate()
print("V79.91-V79.95 INSTALL CHECK PASS")
