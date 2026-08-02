from pathlib import Path
REQUIRED = [
"autonomous_paper_runtime/scheduled_runtime_bundle.py",
"tools/run_scheduled_runtime_bundle_v142_05_to_v142_08.py",
"tools/test_scheduled_runtime_bundle_v142_05_to_v142_08.py",
"tools/install_check_v142_05_to_v142_08.py",
"tools/verify_scheduled_runtime_bundle_v142_05_to_v142_08.py",
"RUN_V142_05_TO_V142_08_ULTRA_FAST.ps1",
"RUN_V142_05_TO_V142_08_TEST_AND_VERIFY.ps1",
"V142_05_TO_V142_08_ULTRA_FAST_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in REQUIRED if not (root/x).exists()]
if missing: raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
