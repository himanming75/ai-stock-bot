from pathlib import Path
R=[
"paper_pilot/validation_analytics.py",
"dashboard/validation_analytics_integration.py",
"tools/run_validation_analytics_op5_05_to_op5_08.py",
"tools/test_validation_analytics_op5_05_to_op5_08.py",
"tools/install_check_op5_05_to_op5_08.py",
"tools/verify_validation_analytics_op5_05_to_op5_08.py",
"RUN_OP5_05_TO_OP5_08_ANALYTICS.ps1",
"RUN_OP5_05_TO_OP5_08_TEST_AND_VERIFY.ps1",
"OP5_05_TO_OP5_08_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[item for item in R if not(root/item).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
