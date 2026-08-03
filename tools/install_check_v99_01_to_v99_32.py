from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
required=[
"ai_portfolio_manager/io.py",
"ai_portfolio_manager/candidates.py",
"ai_portfolio_manager/scoring.py",
"ai_portfolio_manager/allocation.py",
"ai_portfolio_manager/risk.py",
"ai_portfolio_manager/engine.py",
"ai_portfolio_manager/dashboard.py",
"tools/run_v99_01_to_v99_32.py",
"tools/test_v99_01_to_v99_32.py",
"tools/verify_v99_01_to_v99_32.py",
"release/v99_01_to_v99_32/input/portfolio_manager_policy.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
if not (ROOT/"backtest_batch").exists():
    print("MISSING DEPENDENCY: backtest_batch");raise SystemExit(1)
print("V99.01-V99.32 INSTALL CHECK PASS")
