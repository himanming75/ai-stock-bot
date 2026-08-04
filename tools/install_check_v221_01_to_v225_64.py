from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
required = [
    "paper_operations_v2/io.py",
    "paper_operations_v2/config.py",
    "paper_operations_v2/state.py",
    "paper_operations_v2/idempotency.py",
    "paper_operations_v2/lifecycle.py",
    "paper_operations_v2/reconcile.py",
    "paper_operations_v2/recovery.py",
    "paper_operations_v2/engine.py",
    "paper_operations_v2/dashboard.py",
    "web_controller/paper_operations_v2_api.py",
    "tools/run_v221_01_to_v225_64.py",
    "tools/test_v221_01_to_v225_64.py",
    "tools/verify_v221_01_to_v225_64.py",
    "release/v221_01_to_v225_64/config/paper_operations_v2_policy.json",
    "release/v221_01_to_v225_64/docs/PAPER_OPERATIONS_AUTOMATION_V2_GUIDE.md",
]
missing = [x for x in required if not (ROOT / x).exists()]
for path in missing:
    print("MISSING:", path)
if missing:
    raise SystemExit(1)
print("V221.01-V225.64 INSTALL CHECK PASS")
