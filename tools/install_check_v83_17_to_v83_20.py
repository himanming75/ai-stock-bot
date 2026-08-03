
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "paper_runtime/scheduled_supervised_runner_v83_17_20.py",
    "dashboard/scheduled_supervised_runner_integration.py",
    "tools/run_scheduled_supervised_runner_v83_17_to_v83_20.py",
    "tools/test_scheduled_supervised_runner_v83_17_to_v83_20.py",
    "tools/install_check_v83_17_to_v83_20.py",
    "tools/verify_scheduled_supervised_runner_v83_17_to_v83_20.py",
    "RUN_V83_17_TO_V83_20_SCHEDULED_SUPERVISED_RUNNER.ps1",
    "RUN_V83_17_TO_V83_20_TEST_AND_VERIFY.ps1",
    "V83_17_TO_V83_20_MANIFEST.json",
]
missing = [item for item in required if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
