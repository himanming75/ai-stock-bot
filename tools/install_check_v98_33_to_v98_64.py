from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
required=[
"backtest_batch/io.py","backtest_batch/queue.py",
"backtest_batch/executor.py","backtest_batch/retry.py",
"backtest_batch/regression.py","backtest_batch/champion.py",
"backtest_batch/engine.py","backtest_batch/dashboard.py",
"tools/run_v98_33_to_v98_64.py","tools/test_v98_33_to_v98_64.py",
"tools/verify_v98_33_to_v98_64.py",
"release/v98_33_to_v98_64/input/batch_policy.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
if not (ROOT/"automated_backtest").exists():
    print("MISSING DEPENDENCY: automated_backtest");raise SystemExit(1)
print("V98.33-V98.64 INSTALL CHECK PASS")
