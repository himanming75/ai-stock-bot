from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

required=[
"autonomous_paper_operations/io.py",
"autonomous_paper_operations/tournament.py",
"autonomous_paper_operations/sessions.py",
"autonomous_paper_operations/scenario.py",
"autonomous_paper_operations/recovery.py",
"autonomous_paper_operations/backup.py",
"autonomous_paper_operations/report.py",
"autonomous_paper_operations/engine.py",
"autonomous_paper_operations/dashboard.py",
"tools/run_v109_01_to_v110_64.py",
"tools/test_v109_01_to_v110_64.py",
"tools/verify_v109_01_to_v110_64.py",
"release/v109_01_to_v110_64/input/autonomous_operations_policy.json",
"release/v109_01_to_v110_64/scheduler/INSTALL_DAILY_PAPER_TASK.ps1",
"release/v109_01_to_v110_64/scheduler/REMOVE_DAILY_PAPER_TASK.ps1",
]
missing=[item for item in required if not (ROOT/item).exists()]
for item in missing:
    print("MISSING:",item)
if missing:
    raise SystemExit(1)
print("V109.01-V110.64 INSTALL CHECK PASS")
