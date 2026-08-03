
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
required=[
"paper_runtime/supervised_automation_runner_v83_13_16.py",
"dashboard/supervised_automation_runner_integration.py",
"tools/run_supervised_automation_runner_v83_13_to_v83_16.py",
"tools/test_supervised_automation_runner_v83_13_to_v83_16.py",
"tools/install_check_v83_13_to_v83_16.py",
"tools/verify_supervised_automation_runner_v83_13_to_v83_16.py",
"RUN_V83_13_TO_V83_16_SUPERVISED_RUNNER.ps1",
"RUN_V83_13_TO_V83_16_TEST_AND_VERIFY.ps1",
"V83_13_TO_V83_16_MANIFEST.json"]
missing=[x for x in required if not (ROOT/x).exists()]
if missing: raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
