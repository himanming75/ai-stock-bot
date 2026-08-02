from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.terminal_monitor_commit_orchestrator import TerminalMonitorCommitOrchestrator
assert TerminalMonitorCommitOrchestrator
required=ROOT/"release/v133_00/actual/actual_terminal_completion_commit_result.json"
if not required.is_file(): raise SystemExit(f"MISSING V133 ACTUAL RESULT: {required}")
print("V133.01-V134.00 TERMINAL MONITOR COMMIT ORCHESTRATOR INSTALL CHECK PASS")
