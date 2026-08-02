from pathlib import Path
R=[
"paper_pilot/risk_monitor.py",
"dashboard/pilot_risk_integration.py",
"tools/run_paper_risk_monitor_op4_13_to_op4_16.py",
"tools/test_paper_risk_monitor_op4_13_to_op4_16.py",
"tools/install_check_op4_13_to_op4_16.py",
"tools/verify_paper_risk_monitor_op4_13_to_op4_16.py",
"RUN_OP4_13_TO_OP4_16_RISK_MONITOR.ps1",
"RUN_OP4_13_TO_OP4_16_TEST_AND_VERIFY.ps1",
"OP4_13_TO_OP4_16_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
