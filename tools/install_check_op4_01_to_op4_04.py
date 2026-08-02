from pathlib import Path
R=[
"paper_pilot/__init__.py",
"paper_pilot/pilot_foundation.py",
"dashboard/pilot_integration.py",
"tools/run_controlled_paper_pilot_op4_01_to_op4_04.py",
"tools/test_controlled_paper_pilot_op4_01_to_op4_04.py",
"tools/install_check_op4_01_to_op4_04.py",
"tools/verify_controlled_paper_pilot_op4_01_to_op4_04.py",
"RUN_OP4_01_TO_OP4_04_PILOT.ps1",
"RUN_OP4_01_TO_OP4_04_TEST_AND_VERIFY.ps1",
"OP4_01_TO_OP4_04_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
