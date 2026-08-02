from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.order_lifecycle import ExistingPaperOrderLifecycleTracker,LifecycleClass
assert ExistingPaperOrderLifecycleTracker and LifecycleClass
if not (ROOT/"release/v127_00/actual/actual_controlled_paper_single_order_result.json").is_file(): raise SystemExit("MISSING V127 ACTUAL RESULT")
print("V127.01-V128.00 EXISTING PAPER ORDER LIFECYCLE INSTALL CHECK PASS")
