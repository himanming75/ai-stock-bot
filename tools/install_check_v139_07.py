from pathlib import Path
REQUIRED = [
    "autonomous_paper_runtime/autonomous_paper_order_launch.py",
    "tools/run_autonomous_paper_order_launch_v139_07.py",
    "tools/test_autonomous_paper_order_launch_v139_07.py",
    "tools/verify_autonomous_paper_order_launch_v139_07.py",
    "RUN_V139_07_AUTONOMOUS_PAPER_ORDER_LAUNCH.ps1",
    "RUN_V139_07_TEST_AND_VERIFY.ps1",
    "release/v139_07/input/order_candidate.example.json",
    "V139_07_BUNDLE_MANIFEST.json",
]
root = Path(__file__).resolve().parents[1]
missing = [x for x in REQUIRED if not (root / x).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
