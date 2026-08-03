
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "shadow_runtime/scheduler_v82_05_08.py",
    "dashboard/shadow_scheduler_integration.py",
    "tools/run_shadow_scheduler_v82_05_to_v82_08.py",
    "tools/test_shadow_scheduler_v82_05_to_v82_08.py",
    "tools/install_check_v82_05_to_v82_08.py",
    "tools/verify_shadow_scheduler_v82_05_to_v82_08.py",
    "RUN_V82_05_TO_V82_08_SHADOW_SCHEDULER.ps1",
    "RUN_V82_05_TO_V82_08_TEST_AND_VERIFY.ps1",
    "V82_05_TO_V82_08_MANIFEST.json",
]
missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
