
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "paper_runtime/intraday_loop_v82_29_32.py",
    "dashboard/intraday_loop_integration.py",
    "tools/run_intraday_loop_v82_29_to_v82_32.py",
    "tools/test_intraday_loop_v82_29_to_v82_32.py",
    "tools/install_check_v82_29_to_v82_32.py",
    "tools/verify_intraday_loop_v82_29_to_v82_32.py",
    "RUN_V82_29_TO_V82_32_INTRADAY_LOOP.ps1",
    "RUN_V82_29_TO_V82_32_TEST_AND_VERIFY.ps1",
    "V82_29_TO_V82_32_MANIFEST.json",
]
missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
