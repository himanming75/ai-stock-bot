
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "paper_runtime/end_of_day_v82_33_36.py",
    "dashboard/end_of_day_integration.py",
    "tools/run_end_of_day_v82_33_to_v82_36.py",
    "tools/test_end_of_day_v82_33_to_v82_36.py",
    "tools/install_check_v82_33_to_v82_36.py",
    "tools/verify_end_of_day_v82_33_to_v82_36.py",
    "RUN_V82_33_TO_V82_36_END_OF_DAY.ps1",
    "RUN_V82_33_TO_V82_36_TEST_AND_VERIFY.ps1",
    "V82_33_TO_V82_36_MANIFEST.json",
]
missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
