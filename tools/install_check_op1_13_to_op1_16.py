from pathlib import Path
R=["autonomous_paper_runtime/automatic_snapshot_collector.py","tools/run_automatic_snapshot_collector_op1_13_to_op1_16.py","tools/test_automatic_snapshot_collector_op1_13_to_op1_16.py","tools/install_check_op1_13_to_op1_16.py","tools/verify_automatic_snapshot_collector_op1_13_to_op1_16.py","RUN_OP1_13_TO_OP1_16_SNAPSHOT_COLLECTOR.ps1","RUN_OP1_13_TO_OP1_16_TEST_AND_VERIFY.ps1","OP1_13_TO_OP1_16_MANIFEST.json"]
root=Path(__file__).resolve().parents[1];m=[x for x in R if not(root/x).exists()]
if m:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(m))
print("INSTALL_CHECK=PASS")
