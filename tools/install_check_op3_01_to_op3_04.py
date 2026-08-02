from pathlib import Path
R=[
"autonomous_paper_runtime/controlled_paper_order_preparation.py",
"tools/run_controlled_paper_order_preparation_op3_01_to_op3_04.py",
"tools/test_controlled_paper_order_preparation_op3_01_to_op3_04.py",
"tools/install_check_op3_01_to_op3_04.py",
"tools/verify_controlled_paper_order_preparation_op3_01_to_op3_04.py",
"RUN_OP3_01_TO_OP3_04_PAPER_ORDER_PREPARATION.ps1",
"RUN_OP3_01_TO_OP3_04_TEST_AND_VERIFY.ps1",
"OP3_01_TO_OP3_04_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
