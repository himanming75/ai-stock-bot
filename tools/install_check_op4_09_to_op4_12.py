from pathlib import Path
R=[
"paper_pilot/performance_collector.py",
"dashboard/pilot_performance_integration.py",
"tools/run_paper_performance_collector_op4_09_to_op4_12.py",
"tools/test_paper_performance_collector_op4_09_to_op4_12.py",
"tools/install_check_op4_09_to_op4_12.py",
"tools/verify_paper_performance_collector_op4_09_to_op4_12.py",
"RUN_OP4_09_TO_OP4_12_PERFORMANCE.ps1",
"RUN_OP4_09_TO_OP4_12_TEST_AND_VERIFY.ps1",
"OP4_09_TO_OP4_12_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
