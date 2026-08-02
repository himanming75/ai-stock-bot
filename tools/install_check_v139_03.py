from pathlib import Path

REQUIRED = [
    "autonomous_paper_runtime/next_cycle_unlock.py",
    "tools/run_next_cycle_unlock_v139_03.py",
    "tools/test_next_cycle_unlock_v139_03.py",
    "tools/verify_next_cycle_unlock_v139_03.py",
    "RUN_V139_03_NEXT_CYCLE_UNLOCK.ps1",
    "RUN_V139_03_TEST_AND_VERIFY.ps1",
    "V139_03_BUNDLE_MANIFEST.json",
]

root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
