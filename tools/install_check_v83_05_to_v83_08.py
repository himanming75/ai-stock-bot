
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "paper_runtime/local_action_dispatcher_v83_05_08.py",
    "dashboard/local_action_dispatcher_integration.py",
    "tools/run_local_action_dispatcher_v83_05_to_v83_08.py",
    "tools/test_local_action_dispatcher_v83_05_to_v83_08.py",
    "tools/install_check_v83_05_to_v83_08.py",
    "tools/verify_local_action_dispatcher_v83_05_to_v83_08.py",
    "RUN_V83_05_TO_V83_08_LOCAL_ACTION_DISPATCHER.ps1",
    "RUN_V83_05_TO_V83_08_TEST_AND_VERIFY.ps1",
    "V83_05_TO_V83_08_MANIFEST.json",
]
missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
