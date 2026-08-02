from pathlib import Path

REQUIRED = [
    "autonomous_paper_runtime/recovery_validation.py",
    "tools/run_recovery_validation_v139_04.py",
    "tools/test_recovery_validation_v139_04.py",
    "tools/verify_recovery_validation_v139_04.py",
    "RUN_V139_04_RECOVERY_VALIDATION.ps1",
    "RUN_V139_04_TEST_AND_VERIFY.ps1",
    "V139_04_BUNDLE_MANIFEST.json",
]

root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
