from pathlib import Path
import argparse,json,os,sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from autonomous_paper_runtime.final_submission_approval import (
    FinalPaperSubmissionApprovalGate,
)

ENABLE="AI_STOCK_BOT_ENABLE_FINAL_PAPER_SUBMISSION_APPROVAL"
CONFIRM="AI_STOCK_BOT_FINAL_PAPER_SUBMISSION_APPROVAL_CONFIRMATION"


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    a=p.parse_args()

    env=dict(os.environ)
    if env.get(ENABLE,"").upper()!="YES":
        raise SystemExit(f"{ENABLE}=YES is required")

    phrase=env.get(CONFIRM,"")

    root=Path(a.repository_root).resolve()
    preview_result=load(
        root/"release/v137_00/actual/actual_controlled_next_order_execution_preview_result.json"
    )

    gate=FinalPaperSubmissionApprovalGate(
        approval_token_path=root/"release/v138_00/actual/final_submission_approval_token.json",
        approval_audit_path=root/"release/v138_00/actual/final_submission_approval_audit.json",
    )
    report=gate.evaluate(
        preview_result=preview_result,
        order_preview=load(root/"release/v137_00/actual/order_preview.json"),
        risk_snapshot=load(root/"release/v137_00/actual/risk_snapshot.json"),
        exposure_snapshot=load(root/"release/v137_00/actual/exposure_snapshot.json"),
        approval_gate=load(root/"release/v137_00/actual/final_approval_gate.json"),
        approval_phrase=phrase,
        approved_at=datetime.now(timezone.utc).isoformat(),
        network_requests_executed=0,
    )

    out={
        "stage_range":"V137.01-V138.00",
        "status":"PASS",
        "implementation_type":"FINAL_PAPER_SUBMISSION_APPROVAL_GATE",
        "validation_mode":"ACTUAL_SAVED_PREVIEW_FINAL_APPROVAL_LOCAL_ONLY",
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        **report.to_json_dict(),
        "next_phase":(
            "V138_01_EXACTLY_ONE_PAPER_ORDER_SUBMISSION"
            if report.actual_submission_allowed
            else "V138_01_CONTINUE_TERMINAL_MONITOR"
        ),
    }
    path=root/"release/v138_00/actual/actual_final_paper_submission_approval_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0

if __name__=="__main__": raise SystemExit(main())
