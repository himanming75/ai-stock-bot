from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "order_lifecycle_v2/io.py",
    "order_lifecycle_v2/config.py",
    "order_lifecycle_v2/state_machine.py",
    "order_lifecycle_v2/fills.py",
    "order_lifecycle_v2/identity.py",
    "order_lifecycle_v2/duplicates.py",
    "order_lifecycle_v2/recovery.py",
    "order_lifecycle_v2/ledger.py",
    "order_lifecycle_v2/engine.py",
    "order_lifecycle_v2/dashboard.py",
    "web_controller/order_lifecycle_v2_api.py",
    "tools/run_v231_01_to_v235_64.py",
    "tools/test_v231_01_to_v235_64.py",
    "tools/verify_v231_01_to_v235_64.py",
    "release/v231_01_to_v235_64/config/order_lifecycle_v2_policy.json",
    "release/v231_01_to_v235_64/docs/ORDER_LIFECYCLE_V2_GUIDE.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
for x in missing:
    print("MISSING:", x)
if missing:
    raise SystemExit(1)
print("V231.01-V235.64 INSTALL CHECK PASS")
