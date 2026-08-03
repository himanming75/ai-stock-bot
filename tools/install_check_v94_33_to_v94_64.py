from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
required=[
"decision_orchestrator/io.py","decision_orchestrator/planning.py",
"decision_orchestrator/dedup.py","decision_orchestrator/gates.py",
"decision_orchestrator/checklist.py","decision_orchestrator/engine.py",
"decision_orchestrator/dashboard.py","tools/run_v94_33_to_v94_64.py",
"tools/test_v94_33_to_v94_64.py","tools/verify_v94_33_to_v94_64.py",
"release/v94_33_to_v94_64/input/decision_orchestration_policy.json",
"release/v94_33_to_v94_64/input/reference_prices.json",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
if not (ROOT/"meta_strategy_engine").exists():
    print("MISSING DEPENDENCY: meta_strategy_engine"); raise SystemExit(1)
print("V94.33-V94.64 INSTALL CHECK PASS")
