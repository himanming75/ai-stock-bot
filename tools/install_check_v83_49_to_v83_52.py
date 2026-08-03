import importlib
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
required = [
    root / "paper_runtime/supervised_reentry_runner_v83_49_52.py",
    root / "dashboard/supervised_reentry_runner_integration.py",
    root / "tools/run_supervised_reentry_runner_v83_49_to_v83_52.py",
    root / "tools/test_supervised_reentry_runner_v83_49_to_v83_52.py",
    root / "tools/verify_supervised_reentry_runner_v83_49_to_v83_52.py",
    root / "release/v83_49_to_v83_52/input/"
    "supervised_reentry_runner_policy.json",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit("MISSING:\n" + "\n".join(missing))
importlib.import_module(
    "paper_runtime.supervised_reentry_runner_v83_49_52"
)
print("V83.49-V83.52 INSTALL CHECK PASS")
