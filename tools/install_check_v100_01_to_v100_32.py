from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"ai_risk_manager/io.py",
"ai_risk_manager/exposure.py",
"ai_risk_manager/var.py",
"ai_risk_manager/drawdown.py",
"ai_risk_manager/stress.py",
"ai_risk_manager/scoring.py",
"ai_risk_manager/gate.py",
"ai_risk_manager/engine.py",
"ai_risk_manager/dashboard.py",
"tools/run_v100_01_to_v100_32.py",
"tools/test_v100_01_to_v100_32.py",
"tools/verify_v100_01_to_v100_32.py",
"release/v100_01_to_v100_32/input/ai_risk_policy.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:
    print("MISSING:",x)
if missing:
    raise SystemExit(1)

for dependency in ("ai_portfolio_manager","portfolio_rebalance"):
    if not (ROOT/dependency).exists():
        print("MISSING DEPENDENCY:",dependency)
        raise SystemExit(1)

print("V100.01-V100.32 INSTALL CHECK PASS")
