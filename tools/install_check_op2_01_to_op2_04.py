from pathlib import Path

REQUIRED = [
    "autonomous_paper_runtime/shadow_decision_bootstrap.py",
    "tools/run_shadow_decision_bootstrap_op2_01_to_op2_04.py",
    "tools/test_shadow_decision_bootstrap_op2_01_to_op2_04.py",
    "tools/install_check_op2_01_to_op2_04.py",
    "tools/verify_shadow_decision_bootstrap_op2_01_to_op2_04.py",
    "RUN_OP2_01_TO_OP2_04_SHADOW_DECISION.ps1",
    "RUN_OP2_01_TO_OP2_04_TEST_AND_VERIFY.ps1",
    "OP2_01_TO_OP2_04_MANIFEST.json",
]

root = Path(__file__).resolve().parents[1]
missing = [item for item in REQUIRED if not (root/item).exists()]
if missing:
    raise SystemExit("INSTALL_CHECK=FAIL missing=" + ",".join(missing))
print("INSTALL_CHECK=PASS")
