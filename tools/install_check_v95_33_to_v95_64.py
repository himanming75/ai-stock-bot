from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
required=[
"paper_position_lifecycle/io.py",
"paper_position_lifecycle/rules.py",
"paper_position_lifecycle/accounting.py",
"paper_position_lifecycle/state.py",
"paper_position_lifecycle/engine.py",
"paper_position_lifecycle/dashboard.py",
"tools/run_v95_33_to_v95_64.py",
"tools/test_v95_33_to_v95_64.py",
"tools/verify_v95_33_to_v95_64.py",
"release/v95_33_to_v95_64/input/position_lifecycle_policy.json",
"release/v95_33_to_v95_64/input/lifecycle_mark_prices.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
if not (ROOT/"paper_execution_simulator").exists():
    print("MISSING DEPENDENCY: paper_execution_simulator"); raise SystemExit(1)
print("V95.33-V95.64 INSTALL CHECK PASS")
