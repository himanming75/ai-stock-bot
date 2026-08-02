from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.next_order_cycle import ControlledAutonomousNextOrderCycle,NextOrderCycleState
assert ControlledAutonomousNextOrderCycle and NextOrderCycleState
required=ROOT/"release/v135_00/actual/actual_autonomous_next_order_readiness_result.json"
if not required.is_file():
    raise SystemExit(f"MISSING V135 ACTUAL READINESS RESULT: {required}")
print("V135.01-V136.00 CONTROLLED AUTONOMOUS NEXT ORDER CYCLE INSTALL CHECK PASS")
