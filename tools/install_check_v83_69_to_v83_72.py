import importlib
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
required = [
    root / "paper_runtime/operator_control_center_v83_69_72.py",
    root / "dashboard/operator_control_center_integration.py",
    root / "tools/run_operator_control_center_v83_69_to_v83_72.py",
    root / "tools/test_operator_control_center_v83_69_to_v83_72.py",
    root / "tools/verify_operator_control_center_v83_69_to_v83_72.py",
    root / "release/v83_69_to_v83_72/input/"
    "operator_control_center_policy.json",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit("MISSING:\n" + "\n".join(missing))
importlib.import_module(
    "paper_runtime.operator_control_center_v83_69_72"
)
print("V83.69-V83.72 INSTALL CHECK PASS")
