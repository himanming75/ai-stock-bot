
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "shadow_runtime/risk_controller_v82_13_16.py",
    "dashboard/shadow_risk_controller_integration.py",
    "tools/run_shadow_risk_controller_v82_13_to_v82_16.py",
    "tools/test_shadow_risk_controller_v82_13_to_v82_16.py",
    "tools/install_check_v82_13_to_v82_16.py",
    "tools/verify_shadow_risk_controller_v82_13_to_v82_16.py",
    "RUN_V82_13_TO_V82_16_SHADOW_RISK_CONTROLLER.ps1",
    "RUN_V82_13_TO_V82_16_TEST_AND_VERIFY.ps1",
    "V82_13_TO_V82_16_MANIFEST.json",
]
missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
