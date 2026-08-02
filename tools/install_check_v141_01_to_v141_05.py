from pathlib import Path
REQUIRED = [
    "autonomous_paper_runtime/operational_stability_bundle.py",
    "tools/run_operational_stability_bundle_v141_01_to_v141_05.py",
    "tools/test_operational_stability_bundle_v141_01_to_v141_05.py",
    "tools/verify_operational_stability_bundle_v141_01_to_v141_05.py",
    "RUN_V141_01_TO_V141_05_ULTRA_FAST.ps1",
    "RUN_V141_01_TO_V141_05_TEST_AND_VERIFY.ps1",
    "V141_01_TO_V141_05_ULTRA_FAST_MANIFEST.json",
]
root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root/item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
