from pathlib import Path
R=[
"paper_pilot/automation_foundation.py",
"dashboard/pilot_automation_integration.py",
"tools/run_paper_pilot_automation_op4_17_to_op4_20.py",
"tools/test_paper_pilot_automation_op4_17_to_op4_20.py",
"tools/install_check_op4_17_to_op4_20.py",
"tools/verify_paper_pilot_automation_op4_17_to_op4_20.py",
"RUN_OP4_17_TO_OP4_20_AUTOMATION.ps1",
"RUN_OP4_17_TO_OP4_20_TEST_AND_VERIFY.ps1",
"OP4_17_TO_OP4_20_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
