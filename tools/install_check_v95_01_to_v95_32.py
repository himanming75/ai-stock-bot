from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
required=[
"paper_execution_simulator/io.py","paper_execution_simulator/cycle.py",
"paper_execution_simulator/fills.py","paper_execution_simulator/portfolio.py",
"paper_execution_simulator/engine.py","paper_execution_simulator/dashboard.py",
"tools/run_v95_01_to_v95_32.py","tools/test_v95_01_to_v95_32.py",
"tools/verify_v95_01_to_v95_32.py",
"release/v95_01_to_v95_32/input/paper_execution_simulator_policy.json",
"release/v95_01_to_v95_32/input/simulation_mark_prices.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
if not (ROOT/"decision_orchestrator").exists():
    print("MISSING DEPENDENCY: decision_orchestrator"); raise SystemExit(1)
print("V95.01-V95.32 INSTALL CHECK PASS")
