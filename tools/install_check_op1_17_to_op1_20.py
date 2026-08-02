from pathlib import Path
R=["autonomous_paper_runtime/windows_scheduled_read_only_collection.py","tools/run_windows_scheduled_read_only_collection_op1_17_to_op1_20.py","tools/test_windows_scheduled_read_only_collection_op1_17_to_op1_20.py","tools/install_check_op1_17_to_op1_20.py","tools/verify_windows_scheduled_read_only_collection_op1_17_to_op1_20.py","RUN_OP1_17_TO_OP1_20_WINDOWS_SCHEDULE_PLAN.ps1","RUN_OP1_17_TO_OP1_20_TEST_AND_VERIFY.ps1","INSTALL_OP1_READ_ONLY_WINDOWS_TASK.ps1","UNINSTALL_OP1_READ_ONLY_WINDOWS_TASK.ps1","OP1_17_TO_OP1_20_MANIFEST.json"]
root=Path(__file__).resolve().parents[1];m=[x for x in R if not(root/x).exists()]
if m:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(m))
print("INSTALL_CHECK=PASS")
