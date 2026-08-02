from pathlib import Path
R=["autonomous_paper_runtime/automatic_shadow_signal_pipeline.py","tools/run_automatic_shadow_signal_pipeline_op2_13_to_op2_16.py","tools/test_automatic_shadow_signal_pipeline_op2_13_to_op2_16.py","tools/install_check_op2_13_to_op2_16.py","tools/verify_automatic_shadow_signal_pipeline_op2_13_to_op2_16.py","RUN_OP2_13_TO_OP2_16_SHADOW_PIPELINE.ps1","RUN_OP2_13_TO_OP2_16_TEST_AND_VERIFY.ps1","OP2_13_TO_OP2_16_MANIFEST.json"]
root=Path(__file__).resolve().parents[1];m=[x for x in R if not(root/x).exists()]
if m:raise SystemExit("INSTALL_CHECK=FAIL missing="+",".join(m))
print("INSTALL_CHECK=PASS")
