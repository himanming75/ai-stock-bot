from pathlib import Path

REQUIRED = [
    "autonomous_paper_runtime/autonomous_paper_runtime_bundle.py",
    "tools/run_autonomous_paper_runtime_bundle_v142_01_to_v142_04.py",
    "tools/test_autonomous_paper_runtime_bundle_v142_01_to_v142_04.py",
    "tools/install_check_v142_01_to_v142_04.py",
    "tools/verify_autonomous_paper_runtime_bundle_v142_01_to_v142_04.py",
    "RUN_V142_01_TO_V142_04_ULTRA_FAST.ps1",
    "RUN_V142_01_TO_V142_04_TEST_AND_VERIFY.ps1",
    "V142_01_TO_V142_04_ULTRA_FAST_MANIFEST.json",
]

root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root/item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
