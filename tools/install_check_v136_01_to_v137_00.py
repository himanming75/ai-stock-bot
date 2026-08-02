from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.next_order_preview import ControlledNextOrderExecutionPreview,NextOrderPreviewState
assert ControlledNextOrderExecutionPreview and NextOrderPreviewState
required=ROOT/"release/v136_00/actual/actual_controlled_next_order_cycle_result.json"
if not required.is_file():
    raise SystemExit(f"MISSING V136 ACTUAL CYCLE RESULT: {required}")
print("V136.01-V137.00 CONTROLLED NEXT ORDER EXECUTION PREVIEW INSTALL CHECK PASS")
