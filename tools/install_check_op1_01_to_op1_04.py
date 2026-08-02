from pathlib import Path
REQUIRED = [
    "autonomous_paper_runtime/paper_operations_pilot.py",
    "tools/run_paper_operations_pilot_op1_01_to_op1_04.py",
    "tools/test_paper_operations_pilot_op1_01_to_op1_04.py",
    "tools/install_check_op1_01_to_op1_04.py",
    "tools/verify_paper_operations_pilot_op1_01_to_op1_04.py",
    "RUN_OP1_01_TO_OP1_04_PAPER_OPERATIONS_PILOT.ps1",
    "RUN_OP1_01_TO_OP1_04_TEST_AND_VERIFY.ps1",
    "OP1_01_TO_OP1_04_MANIFEST.json",
]
root = Path(__file__).resolve().parents[1]
missing = [x for x in REQUIRED if not (root/x).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
