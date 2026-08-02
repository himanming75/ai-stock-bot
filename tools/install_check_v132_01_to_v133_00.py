from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.terminal_commit import TerminalCompletionCommitter,TerminalCommitState
assert TerminalCompletionCommitter and TerminalCommitState
required=ROOT/"release/v132_00/actual/actual_continued_monitor_terminal_transition_result.json"
if not required.is_file(): raise SystemExit(f"MISSING V132 ACTUAL RESULT: {required}")
print("V132.01-V133.00 TERMINAL COMPLETION COMMIT INSTALL CHECK PASS")
