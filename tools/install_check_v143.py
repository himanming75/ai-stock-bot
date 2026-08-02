from pathlib import Path
R=["autonomous_paper_runtime/final_production_release.py","tools/run_final_production_release_v143.py","tools/test_final_production_release_v143.py","tools/install_check_v143.py","tools/verify_final_production_release_v143.py","RUN_V143_FINAL_PRODUCTION_RELEASE.ps1","RUN_V143_TEST_AND_VERIFY.ps1","V143_FINAL_PRODUCTION_MANIFEST.json"]
root=Path(__file__).resolve().parents[1];m=[x for x in R if not(root/x).exists()]
if m:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(m))
print("INSTALL_CHECK=PASS")
