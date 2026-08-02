from pathlib import Path
R=[
"paper_pilot/multi_day_validation.py",
"dashboard/multi_day_validation_integration.py",
"tools/run_multi_day_paper_validation_op5_01_to_op5_04.py",
"tools/test_multi_day_paper_validation_op5_01_to_op5_04.py",
"tools/install_check_op5_01_to_op5_04.py",
"tools/verify_multi_day_paper_validation_op5_01_to_op5_04.py",
"RUN_OP5_01_TO_OP5_04_VALIDATION.ps1",
"RUN_OP5_01_TO_OP5_04_TEST_AND_VERIFY.ps1",
"OP5_01_TO_OP5_04_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[item for item in R if not(root/item).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
