from pathlib import Path
R=[
"dashboard/__init__.py","dashboard/data_loader.py","dashboard/panels.py",
"dashboard/server.py","dashboard/static/index.html","dashboard/static/styles.css",
"dashboard/static/app.js","tools/build_dashboard_snapshot_dash1_01_to_dash1_04.py",
"tools/test_dashboard_foundation_dash1_01_to_dash1_04.py",
"tools/install_check_dash1_01_to_dash1_04.py",
"tools/verify_dashboard_foundation_dash1_01_to_dash1_04.py",
"RUN_DASH1_01_TO_DASH1_04_DASHBOARD.ps1",
"RUN_DASH1_01_TO_DASH1_04_TEST_AND_VERIFY.ps1",
"DASH1_01_TO_DASH1_04_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing: raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
