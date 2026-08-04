from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"risk_budget/io.py",
"risk_budget/kelly.py",
"risk_budget/volatility.py",
"risk_budget/candidates.py",
"risk_budget/allocation.py",
"risk_budget/exposure.py",
"risk_budget/heat.py",
"risk_budget/gate.py",
"risk_budget/engine.py",
"risk_budget/dashboard.py",
"tools/run_v100_33_to_v100_64.py",
"tools/test_v100_33_to_v100_64.py",
"tools/verify_v100_33_to_v100_64.py",
"release/v100_33_to_v100_64/input/risk_budget_policy.json",
"release/v100_33_to_v100_64/input/strategy_risk_metrics.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

for dependency in ("ai_portfolio_manager","ai_risk_manager"):
    if not (ROOT/dependency).exists():
        print("MISSING DEPENDENCY:",dependency)
        raise SystemExit(1)

print("V100.33-V100.64 INSTALL CHECK PASS")
