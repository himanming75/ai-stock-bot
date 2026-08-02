from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.terminal_transition_gate import ContinuedActualOrderMonitorTerminalTransitionGate
assert ContinuedActualOrderMonitorTerminalTransitionGate
required=ROOT/"release/v131_00/output/order_completion_next_order_unlock_result.json"
if not required.is_file(): raise SystemExit(f"MISSING V131 RESULT: {required}")
print("V131.01-V132.00 CONTINUED ACTUAL ORDER MONITOR TERMINAL TRANSITION INSTALL CHECK PASS")
