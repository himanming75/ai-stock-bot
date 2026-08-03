
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "paper_runtime/multi_day_runtime_v82_37_40.py",
    "dashboard/multi_day_runtime_integration.py",
    "tools/run_multi_day_runtime_v82_37_to_v82_40.py",
    "tools/test_multi_day_runtime_v82_37_to_v82_40.py",
    "tools/install_check_v82_37_to_v82_40.py",
    "tools/verify_multi_day_runtime_v82_37_to_v82_40.py",
    "RUN_V82_37_TO_V82_40_MULTI_DAY_RUNTIME.ps1",
    "RUN_V82_37_TO_V82_40_TEST_AND_VERIFY.ps1",
    "V82_37_TO_V82_40_MANIFEST.json",
]
missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
