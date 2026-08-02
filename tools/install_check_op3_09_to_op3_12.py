from pathlib import Path
R=[
"autonomous_paper_runtime/paper_order_lifecycle_reconciliation.py",
"tools/run_paper_order_lifecycle_op3_09_to_op3_12.py",
"tools/test_paper_order_lifecycle_op3_09_to_op3_12.py",
"tools/install_check_op3_09_to_op3_12.py",
"tools/verify_paper_order_lifecycle_op3_09_to_op3_12.py",
"RUN_OP3_09_TO_OP3_12_PAPER_LIFECYCLE.ps1",
"RUN_OP3_09_TO_OP3_12_TEST_AND_VERIFY.ps1",
"OP3_09_TO_OP3_12_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
