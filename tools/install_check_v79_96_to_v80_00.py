from pathlib import Path
import importlib, sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
required = [
    "alpaca_market_data/historical_backtest_completion_v79_96_v80_00.py",
    "tools/run_v79_96_to_v80_00_pipeline.py",
    "tools/test_historical_backtest_completion_v79_96_to_v80_00.py",
    "tools/verify_v79_96_to_v80_00_pipeline.py",
    "release/v79_96/config/historical_backtest_completion_config_v79_96.json",
]
missing = [path for path in required if not (ROOT / path).is_file()]
if missing:
    raise SystemExit("MISSING: " + ", ".join(missing))
module = importlib.import_module(
    "alpaca_market_data.historical_backtest_completion_v79_96_v80_00"
)
module.BacktestCompletionConfig().validate()
print("V79.96-V80.00 INSTALL CHECK PASS")
