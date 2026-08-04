from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"autonomous_orchestrator/io.py","autonomous_orchestrator/market.py",
"autonomous_orchestrator/scanner.py","autonomous_orchestrator/selector.py",
"autonomous_orchestrator/planner.py","autonomous_orchestrator/execution.py",
"autonomous_orchestrator/positions.py","autonomous_orchestrator/performance.py",
"autonomous_orchestrator/checkpoint.py","autonomous_orchestrator/engine.py",
"autonomous_orchestrator/dashboard.py","tools/run_v137_01_to_v139_64.py",
"tools/test_v137_01_to_v139_64.py","tools/verify_v137_01_to_v139_64.py",
"release/v137_01_to_v139_64/input/autonomous_orchestrator_policy.json",
"release/v137_01_to_v139_64/input/autonomous_orchestrator_fixture.json",
"release/v137_01_to_v139_64/docs/AUTONOMOUS_ORCHESTRATOR_GUIDE.md",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing: print("MISSING:",x)
if missing: raise SystemExit(1)
print("V137.01-V139.64 INSTALL CHECK PASS")
