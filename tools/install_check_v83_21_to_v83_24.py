
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "paper_runtime/scheduled_run_dispatch_v83_21_24.py",
    "dashboard/scheduled_run_dispatch_integration.py",
    "tools/run_scheduled_run_dispatch_v83_21_to_v83_24.py",
    "tools/test_scheduled_run_dispatch_v83_21_to_v83_24.py",
    "tools/install_check_v83_21_to_v83_24.py",
    "tools/verify_scheduled_run_dispatch_v83_21_to_v83_24.py",
    "RUN_V83_21_TO_V83_24_SCHEDULED_RUN_DISPATCH.ps1",
    "RUN_V83_21_TO_V83_24_TEST_AND_VERIFY.ps1",
    "V83_21_TO_V83_24_MANIFEST.json",
]
missing = [item for item in required if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
