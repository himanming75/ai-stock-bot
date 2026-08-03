
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "paper_runtime/automatic_schedule_evaluation_v83_25_28.py",
    "dashboard/automatic_schedule_evaluation_integration.py",
    "tools/run_automatic_schedule_evaluation_v83_25_to_v83_28.py",
    "tools/test_automatic_schedule_evaluation_v83_25_to_v83_28.py",
    "tools/install_check_v83_25_to_v83_28.py",
    "tools/verify_automatic_schedule_evaluation_v83_25_to_v83_28.py",
    "RUN_V83_25_TO_V83_28_AUTOMATIC_SCHEDULE_EVALUATION.ps1",
    "RUN_V83_25_TO_V83_28_TEST_AND_VERIFY.ps1",
    "V83_25_TO_V83_28_MANIFEST.json",
]
missing = [item for item in required if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
