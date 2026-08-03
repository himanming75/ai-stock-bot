from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"portfolio_rebalance/io.py",
"portfolio_rebalance/models.py",
"portfolio_rebalance/mapping.py",
"portfolio_rebalance/planner.py",
"portfolio_rebalance/turnover.py",
"portfolio_rebalance/dedup.py",
"portfolio_rebalance/risk.py",
"portfolio_rebalance/engine.py",
"portfolio_rebalance/dashboard.py",
"tools/run_v99_33_to_v99_64.py",
"tools/test_v99_33_to_v99_64.py",
"tools/verify_v99_33_to_v99_64.py",
"release/v99_33_to_v99_64/input/rebalance_policy.json",
"release/v99_33_to_v99_64/input/reference_prices.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

for dependency in ("ai_portfolio_manager","paper_account_ledger"):
    if not (ROOT/dependency).exists():
        print("MISSING DEPENDENCY:",dependency)
        raise SystemExit(1)

print("V99.33-V99.64 INSTALL CHECK PASS")
