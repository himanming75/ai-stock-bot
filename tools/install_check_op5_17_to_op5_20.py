from pathlib import Path
R=[
"paper_pilot/promotion_approval.py",
"dashboard/promotion_approval_integration.py",
"tools/run_promotion_approval_op5_17_to_op5_20.py",
"tools/test_promotion_approval_op5_17_to_op5_20.py",
"tools/install_check_op5_17_to_op5_20.py",
"tools/verify_promotion_approval_op5_17_to_op5_20.py",
"RUN_OP5_17_TO_OP5_20_APPROVAL.ps1",
"RUN_OP5_17_TO_OP5_20_TEST_AND_VERIFY.ps1",
"OP5_17_TO_OP5_20_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
