
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "paper_runtime/scheduler_v82_25_28.py",
    "dashboard/paper_scheduler_integration.py",
    "tools/run_paper_scheduler_v82_25_to_v82_28.py",
    "tools/test_paper_scheduler_v82_25_to_v82_28.py",
    "tools/install_check_v82_25_to_v82_28.py",
    "tools/verify_paper_scheduler_v82_25_to_v82_28.py",
    "RUN_V82_25_TO_V82_28_PAPER_SCHEDULER.ps1",
    "RUN_V82_25_TO_V82_28_TEST_AND_VERIFY.ps1",
    "V82_25_TO_V82_28_MANIFEST.json",
]
missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
