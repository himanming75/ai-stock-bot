from pathlib import Path
R=[
"autonomous_paper_runtime/current_paper_snapshot_collector.py",
"dashboard/paper_trading_integration.py",
"dashboard/advanced_monitoring.py",
"tools/run_current_paper_snapshot_collector_dash2_05.py",
"tools/test_current_paper_snapshot_hotfix_dash2_05.py",
"tools/install_check_dash2_05.py",
"tools/verify_current_paper_snapshot_hotfix_dash2_05.py",
"RUN_DASH2_05_REFRESH_ACTUAL_PAPER_SNAPSHOT.ps1",
"RUN_DASH2_05_TEST_AND_VERIFY.ps1",
"DASH2_05_ACTUAL_SNAPSHOT_HOTFIX_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
