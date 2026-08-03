
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "shadow_runtime/performance_analytics_v82_09_12.py",
    "dashboard/shadow_performance_integration.py",
    "tools/run_shadow_performance_v82_09_to_v82_12.py",
    "tools/test_shadow_performance_v82_09_to_v82_12.py",
    "tools/install_check_v82_09_to_v82_12.py",
    "tools/verify_shadow_performance_v82_09_to_v82_12.py",
    "RUN_V82_09_TO_V82_12_SHADOW_PERFORMANCE.ps1",
    "RUN_V82_09_TO_V82_12_TEST_AND_VERIFY.ps1",
    "V82_09_TO_V82_12_MANIFEST.json",
]
missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
