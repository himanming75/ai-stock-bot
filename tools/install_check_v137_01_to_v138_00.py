from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from autonomous_paper_runtime.final_submission_approval import FinalPaperSubmissionApprovalGate,FinalSubmissionApprovalState
assert FinalPaperSubmissionApprovalGate and FinalSubmissionApprovalState
required=ROOT/"release/v137_00/actual/actual_controlled_next_order_execution_preview_result.json"
if not required.is_file():
    raise SystemExit(f"MISSING V137 ACTUAL PREVIEW RESULT: {required}")
print("V137.01-V138.00 FINAL PAPER SUBMISSION APPROVAL INSTALL CHECK PASS")
