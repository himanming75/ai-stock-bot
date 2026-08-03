import importlib
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
required = [
    root / "paper_runtime/end_to_end_paper_cycle_certification_v83_65_68.py",
    root / "dashboard/end_to_end_paper_cycle_certification_integration.py",
    root / "tools/run_end_to_end_paper_cycle_certification_v83_65_to_v83_68.py",
    root / "tools/test_end_to_end_paper_cycle_certification_v83_65_to_v83_68.py",
    root / "tools/verify_end_to_end_paper_cycle_certification_v83_65_to_v83_68.py",
    root / "release/v83_65_to_v83_68/input/"
    "end_to_end_paper_cycle_certification_policy.json",
    root / "release/v83_65_to_v83_68/input/"
    "end_to_end_paper_cycle_scenario_overrides.json",
]
missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit("MISSING:\n" + "\n".join(missing))
importlib.import_module(
    "paper_runtime.end_to_end_paper_cycle_certification_v83_65_68"
)
print("V83.65-V83.68 INSTALL CHECK PASS")
