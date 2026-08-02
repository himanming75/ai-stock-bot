from pathlib import Path
R=["dashboard/advanced_monitoring.py","dashboard/server.py","dashboard/static/index.html","dashboard/static/styles.css","dashboard/static/app.js","tools/build_dashboard_advanced_snapshot_dash1_05_to_dash1_08.py","tools/test_dashboard_advanced_dash1_05_to_dash1_08.py","tools/install_check_dash1_05_to_dash1_08.py","tools/verify_dashboard_advanced_dash1_05_to_dash1_08.py","RUN_DASH1_05_TO_DASH1_08_TEST_AND_VERIFY.ps1","DASH1_05_TO_DASH1_08_MANIFEST.json"]
root=Path(__file__).resolve().parents[1];m=[x for x in R if not(root/x).exists()]
if m:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(m))
print("INSTALL_CHECK=PASS")
