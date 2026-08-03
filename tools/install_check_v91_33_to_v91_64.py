from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"parameter_optimizer/io.py",
"parameter_optimizer/search_space.py",
"parameter_optimizer/walk_forward.py",
"parameter_optimizer/scoring.py",
"parameter_optimizer/engine.py",
"parameter_optimizer/dashboard.py",
"tools/run_v91_33_to_v91_64.py",
"tools/test_v91_33_to_v91_64.py",
"tools/verify_v91_33_to_v91_64.py",
"release/v91_33_to_v91_64/input/optimization_policy.json",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)

for dependency in ("v89_engine","strategy_lab"):
    if not (ROOT/dependency).exists():
        print("MISSING DEPENDENCY:",dependency)
        raise SystemExit(1)

print("V91.33-V91.64 INSTALL CHECK PASS")
