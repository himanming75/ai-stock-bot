
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "paper_runtime/controlled_automation_cycle_v83_09_12.py",
    "dashboard/controlled_automation_cycle_integration.py",
    "tools/run_controlled_automation_cycle_v83_09_to_v83_12.py",
    "tools/test_controlled_automation_cycle_v83_09_to_v83_12.py",
    "tools/install_check_v83_09_to_v83_12.py",
    "tools/verify_controlled_automation_cycle_v83_09_to_v83_12.py",
    "RUN_V83_09_TO_V83_12_CONTROLLED_AUTOMATION_CYCLE.ps1",
    "RUN_V83_09_TO_V83_12_TEST_AND_VERIFY.ps1",
    "V83_09_TO_V83_12_MANIFEST.json",
]
missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
