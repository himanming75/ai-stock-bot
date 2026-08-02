from pathlib import Path
REQUIRED = [
    "autonomous_paper_runtime/next_order_eligibility.py",
    "tools/run_next_order_eligibility_v139_06.py",
    "tools/test_next_order_eligibility_v139_06.py",
    "tools/verify_next_order_eligibility_v139_06.py",
    "RUN_V139_06_NEXT_ORDER_ELIGIBILITY.ps1",
    "RUN_V139_06_TEST_AND_VERIFY.ps1",
    "release/v139_06/input/next_order_eligibility_snapshot.example.json",
    "V139_06_BUNDLE_MANIFEST.json",
]
root = Path(__file__).resolve().parents[1]
missing = [x for x in REQUIRED if not (root / x).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
