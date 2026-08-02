from pathlib import Path
R=[
"paper_pilot/session_monitor.py",
"dashboard/pilot_monitor_integration.py",
"tools/run_paper_session_monitor_op4_05_to_op4_08.py",
"tools/test_paper_session_monitor_op4_05_to_op4_08.py",
"tools/install_check_op4_05_to_op4_08.py",
"tools/verify_paper_session_monitor_op4_05_to_op4_08.py",
"RUN_OP4_05_TO_OP4_08_SESSION_MONITOR.ps1",
"RUN_OP4_05_TO_OP4_08_TEST_AND_VERIFY.ps1",
"OP4_05_TO_OP4_08_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
