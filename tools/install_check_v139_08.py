from pathlib import Path
REQUIRED = [
    "autonomous_paper_runtime/submitted_order_acceptance_verification.py",
    "tools/run_submitted_order_acceptance_verification_v139_08.py",
    "tools/test_submitted_order_acceptance_verification_v139_08.py",
    "tools/verify_submitted_order_acceptance_verification_v139_08.py",
    "RUN_V139_08_SUBMITTED_ORDER_ACCEPTANCE_VERIFICATION.ps1",
    "RUN_V139_08_TEST_AND_VERIFY.ps1",
    "release/v139_08/input/submitted_order_result_snapshot.example.json",
    "V139_08_BUNDLE_MANIFEST.json",
]
root = Path(__file__).resolve().parents[1]
missing = [x for x in REQUIRED if not (root / x).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
