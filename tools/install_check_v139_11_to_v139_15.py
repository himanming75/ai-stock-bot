from pathlib import Path
REQUIRED = [
    "autonomous_paper_runtime/ultra_fast_cycle_finalization.py",
    "tools/run_ultra_fast_cycle_finalization_v139_11_to_v139_15.py",
    "tools/test_ultra_fast_cycle_finalization_v139_11_to_v139_15.py",
    "tools/verify_ultra_fast_cycle_finalization_v139_11_to_v139_15.py",
    "RUN_V139_11_TO_V139_15_ULTRA_FAST.ps1",
    "RUN_V139_11_TO_V139_15_TEST_AND_VERIFY.ps1",
    "release/v139_11_to_v139_15/input/portfolio_reconciliation_snapshot.example.json",
    "V139_11_TO_V139_15_ULTRA_FAST_MANIFEST.json",
]
root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root / item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
