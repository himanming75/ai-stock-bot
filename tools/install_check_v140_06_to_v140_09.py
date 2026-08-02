from pathlib import Path
R=["autonomous_paper_runtime/autonomous_engine_bundle.py","tools/run_autonomous_engine_bundle_v140_06_to_v140_09.py","tools/test_autonomous_engine_bundle_v140_06_to_v140_09.py","tools/verify_autonomous_engine_bundle_v140_06_to_v140_09.py","RUN_V140_06_TO_V140_09_ULTRA_FAST.ps1","RUN_V140_06_TO_V140_09_TEST_AND_VERIFY.ps1","V140_06_TO_V140_09_ULTRA_FAST_MANIFEST.json"]
root=Path(__file__).resolve().parents[1];m=[x for x in R if not(root/x).exists()]
print("INSTALL_CHECK=PASS") if not m else (_ for _ in ()).throw(SystemExit("INSTALL_CHECK=FAIL missing="+",".join(m)))
