from pathlib import Path

REQUIRED = [
    "autonomous_paper_runtime/active_order_lifecycle_monitor.py",
    "tools/run_active_order_lifecycle_monitor_v139_09.py",
    "tools/test_active_order_lifecycle_monitor_v139_09.py",
    "tools/verify_active_order_lifecycle_monitor_v139_09.py",
    "RUN_V139_09_ACTIVE_ORDER_LIFECYCLE_MONITOR.ps1",
    "RUN_V139_09_TEST_AND_VERIFY.ps1",
    "release/v139_09/input/active_order_lifecycle_snapshot.example.json",
    "V139_09_BUNDLE_MANIFEST.json",
]

root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
