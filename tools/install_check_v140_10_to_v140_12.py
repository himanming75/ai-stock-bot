from pathlib import Path
REQUIRED = [
    "autonomous_paper_runtime/alpaca_paper_integration_bundle.py",
    "tools/run_alpaca_paper_integration_bundle_v140_10_to_v140_12.py",
    "tools/test_alpaca_paper_integration_bundle_v140_10_to_v140_12.py",
    "tools/verify_alpaca_paper_integration_bundle_v140_10_to_v140_12.py",
    "RUN_V140_10_TO_V140_12_ULTRA_FAST.ps1",
    "RUN_V140_10_TO_V140_12_TEST_AND_VERIFY.ps1",
    "V140_10_TO_V140_12_ULTRA_FAST_MANIFEST.json",
]
root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root/item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
