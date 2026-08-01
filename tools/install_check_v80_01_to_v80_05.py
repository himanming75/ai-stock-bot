from pathlib import Path
import importlib, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
required = [
    "alpaca_market_data/paper_trading_readiness_v80_01_05.py",
    "tools/run_v80_01_to_v80_05_pipeline.py",
    "tools/test_paper_trading_readiness_v80_01_to_v80_05.py",
    "tools/verify_v80_01_to_v80_05_pipeline.py",
    "release/v80_01/config/paper_trading_readiness_config_v80_01.json",
]
missing = [path for path in required if not (ROOT / path).is_file()]
if missing:
    raise SystemExit("MISSING: " + ", ".join(missing))
module = importlib.import_module(
    "alpaca_market_data.paper_trading_readiness_v80_01_05"
)
module.PaperReadinessConfig().validate()
print("V80.01-V80.05 INSTALL CHECK PASS")
