from pathlib import Path
R=["dashboard/paper_trading_integration.py","dashboard/server.py","dashboard/static/index.html","dashboard/static/styles.css","dashboard/static/app.js","tools/build_paper_dashboard_snapshot_dash2_01_to_dash2_04.py","tools/test_paper_dashboard_integration_dash2_01_to_dash2_04.py","tools/install_check_dash2_01_to_dash2_04.py","tools/verify_paper_dashboard_integration_dash2_01_to_dash2_04.py","RUN_DASH2_01_TO_DASH2_04_TEST_AND_VERIFY.ps1","DASH2_01_TO_DASH2_04_MANIFEST.json"]
root=Path(__file__).resolve().parents[1];m=[x for x in R if not(root/x).exists()]
if m:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(m))
print("INSTALL_CHECK=PASS")
