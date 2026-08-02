from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.next_order_readiness import AutonomousNextOrderReadinessGate,NextOrderReadinessState
assert AutonomousNextOrderReadinessGate and NextOrderReadinessState
required=ROOT/"release/v134_00/actual/actual_terminal_monitor_commit_orchestrator_result.json"
if not required.is_file(): raise SystemExit(f"MISSING V134 ACTUAL RESULT: {required}")
print("V134.01-V135.00 AUTONOMOUS NEXT ORDER READINESS INSTALL CHECK PASS")
