
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "shadow_runtime/trade_authorization_v82_17_20.py",
    "dashboard/shadow_trade_authorization_integration.py",
    "tools/run_shadow_trade_authorization_v82_17_to_v82_20.py",
    "tools/test_shadow_trade_authorization_v82_17_to_v82_20.py",
    "tools/install_check_v82_17_to_v82_20.py",
    "tools/verify_shadow_trade_authorization_v82_17_to_v82_20.py",
    "RUN_V82_17_TO_V82_20_SHADOW_TRADE_AUTHORIZATION.ps1",
    "RUN_V82_17_TO_V82_20_TEST_AND_VERIFY.ps1",
    "V82_17_TO_V82_20_MANIFEST.json",
]
missing = [item for item in REQUIRED if not (ROOT / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
