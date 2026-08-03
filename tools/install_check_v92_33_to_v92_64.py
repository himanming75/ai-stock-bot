from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"enterprise_risk_center/io.py",
"enterprise_risk_center/statistics.py",
"enterprise_risk_center/stress.py",
"enterprise_risk_center/monte_carlo.py",
"enterprise_risk_center/guards.py",
"enterprise_risk_center/engine.py",
"enterprise_risk_center/dashboard.py",
"tools/run_v92_33_to_v92_64.py",
"tools/test_v92_33_to_v92_64.py",
"tools/verify_v92_33_to_v92_64.py",
"release/v92_33_to_v92_64/input/enterprise_risk_policy.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

for dependency in (
    "parameter_optimizer",
    "ai_explainability_pro",
):
    if not (ROOT/dependency).exists():
        print("MISSING DEPENDENCY:",dependency)
        raise SystemExit(1)

print("V92.33-V92.64 INSTALL CHECK PASS")
