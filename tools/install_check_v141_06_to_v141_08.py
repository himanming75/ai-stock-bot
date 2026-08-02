from pathlib import Path

REQUIRED = [
    "autonomous_paper_runtime/final_validation_release_bundle.py",
    "tools/run_final_validation_release_bundle_v141_06_to_v141_08.py",
    "tools/test_final_validation_release_bundle_v141_06_to_v141_08.py",
    "tools/verify_final_validation_release_bundle_v141_06_to_v141_08.py",
    "RUN_V141_06_TO_V141_08_ULTRA_FAST.ps1",
    "RUN_V141_06_TO_V141_08_TEST_AND_VERIFY.ps1",
    "V141_06_TO_V141_08_ULTRA_FAST_MANIFEST.json",
]

root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root/item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
