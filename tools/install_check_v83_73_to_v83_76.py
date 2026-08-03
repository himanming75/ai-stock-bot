import importlib
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
required = [
    root / "paper_runtime/paper_autonomous_mode_v83_73_76.py",
    root / "dashboard/paper_autonomous_mode_integration.py",
    root / "tools/run_paper_autonomous_mode_v83_73_to_v83_76.py",
    root / "tools/test_paper_autonomous_mode_v83_73_to_v83_76.py",
    root / "tools/verify_paper_autonomous_mode_v83_73_to_v83_76.py",
    root / "release/v83_73_to_v83_76/input/"
    "paper_autonomous_mode_policy.json",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit("MISSING:\n" + "\n".join(missing))
importlib.import_module("paper_runtime.paper_autonomous_mode_v83_73_76")
print("V83.73-V83.76 INSTALL CHECK PASS")
