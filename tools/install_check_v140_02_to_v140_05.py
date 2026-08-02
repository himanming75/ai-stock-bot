from pathlib import Path
REQUIRED=[
"autonomous_paper_runtime/runtime_control_bundle.py",
"tools/run_runtime_control_bundle_v140_02_to_v140_05.py",
"tools/test_runtime_control_bundle_v140_02_to_v140_05.py",
"tools/verify_runtime_control_bundle_v140_02_to_v140_05.py",
"RUN_V140_02_TO_V140_05_ULTRA_FAST.ps1",
"RUN_V140_02_TO_V140_05_TEST_AND_VERIFY.ps1",
"V140_02_TO_V140_05_ULTRA_FAST_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in REQUIRED if not (root/x).exists()]
if missing: raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
