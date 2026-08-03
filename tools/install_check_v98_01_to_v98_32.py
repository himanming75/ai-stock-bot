from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"automated_backtest/io.py",
"automated_backtest/discovery.py",
"automated_backtest/matrix.py",
"automated_backtest/data.py",
"automated_backtest/strategies.py",
"automated_backtest/runner.py",
"automated_backtest/cache.py",
"automated_backtest/aggregation.py",
"automated_backtest/engine.py",
"automated_backtest/dashboard.py",
"tools/run_v98_01_to_v98_32.py",
"tools/test_v98_01_to_v98_32.py",
"tools/verify_v98_01_to_v98_32.py",
"release/v98_01_to_v98_32/input/automated_backtest_policy.json",
"release/v98_01_to_v98_32/data/sample_ohlcv.csv",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

if not (ROOT/"paper_broker_read_model").exists():
    print("MISSING DEPENDENCY: paper_broker_read_model")
    raise SystemExit(1)

print("V98.01-V98.32 INSTALL CHECK PASS")
