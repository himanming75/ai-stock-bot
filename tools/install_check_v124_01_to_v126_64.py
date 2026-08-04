from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"continuous_paper_shadow/io.py","continuous_paper_shadow/signals.py",
"continuous_paper_shadow/planner.py","continuous_paper_shadow/gate.py",
"continuous_paper_shadow/shadow.py","continuous_paper_shadow/qualification.py",
"continuous_paper_shadow/engine.py","tools/run_v124_01_to_v126_64.py",
"tools/test_v124_01_to_v126_64.py","tools/verify_v124_01_to_v126_64.py",
"release/v124_01_to_v126_64/input/continuous_paper_shadow_policy.json",
"release/v124_01_to_v126_64/input/continuous_paper_shadow_fixture.json",
"release/v124_01_to_v126_64/scheduler/INSTALL_CONTINUOUS_PAPER_TASK.ps1",
]
missing=[x for x in required if not (ROOT/x).exists()]
for x in missing:print("MISSING:",x)
if missing:raise SystemExit(1)
print("V124.01-V126.64 INSTALL CHECK PASS")
