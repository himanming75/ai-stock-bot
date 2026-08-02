from pathlib import Path
R=[
"autonomous_paper_runtime/single_controlled_paper_order_execution.py",
"tools/run_single_controlled_paper_order_execution_op3_05_to_op3_08.py",
"tools/test_single_controlled_paper_order_execution_op3_05_to_op3_08.py",
"tools/install_check_op3_05_to_op3_08.py",
"tools/verify_single_controlled_paper_order_execution_op3_05_to_op3_08.py",
"RUN_OP3_05_TO_OP3_08_SINGLE_PAPER_ORDER.ps1",
"RUN_OP3_05_TO_OP3_08_TEST_AND_VERIFY.ps1",
"OP3_05_TO_OP3_08_MANIFEST.json"]
root=Path(__file__).resolve().parents[1]
missing=[x for x in R if not(root/x).exists()]
if missing:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(missing))
print("INSTALL_CHECK=PASS")
