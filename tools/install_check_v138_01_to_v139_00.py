from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.cycle_continuation import AutonomousCycleContinuationOrchestrator
assert AutonomousCycleContinuationOrchestrator
required=[
    ROOT/"release/v134_00/actual/actual_terminal_monitor_commit_orchestrator_result.json",
    ROOT/"release/v135_00/actual/actual_autonomous_next_order_readiness_result.json",
    ROOT/"release/v138_00/actual/actual_final_paper_submission_approval_result.json",
]
missing=[str(x) for x in required if not x.is_file()]
if missing: raise SystemExit("MISSING REQUIRED RESULTS: "+", ".join(missing))
print("V138.01-V139.00 AUTONOMOUS CYCLE CONTINUATION INSTALL CHECK PASS")
