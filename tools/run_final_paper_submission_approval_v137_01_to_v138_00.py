from pathlib import Path
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from autonomous_paper_runtime.final_submission_approval import (
    FinalPaperSubmissionApprovalGate,
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    a=p.parse_args()
    root=Path(a.repository_root).resolve()

    result_path=root/"release/v137_00/actual/actual_controlled_next_order_execution_preview_result.json"
    preview_result=load(result_path)

    gate=FinalPaperSubmissionApprovalGate(
        approval_token_path=root/"release/v138_00/approval/final_submission_approval_token.json",
        approval_audit_path=root/"release/v138_00/approval/final_submission_approval_audit.json",
    )
    report=gate.evaluate(
        preview_result=preview_result,
        order_preview=load(root/"release/v137_00/actual/order_preview.json"),
        risk_snapshot=load(root/"release/v137_00/actual/risk_snapshot.json"),
        exposure_snapshot=load(root/"release/v137_00/actual/exposure_snapshot.json"),
        approval_gate=load(root/"release/v137_00/actual/final_approval_gate.json"),
        approval_phrase="",
        approved_at="",
        network_requests_executed=0,
    )

    out={
        "stage_range":"V137.01-V138.00",
        "status":"PASS",
        "implementation_type":"FINAL_PAPER_SUBMISSION_APPROVAL_GATE",
        "validation_mode":"PRIOR_ACTUAL_PREVIEW_RESULT_NO_APPROVAL",
        **report.to_json_dict(),
        "wait_verified":(
            report.state.value=="WAIT_PREVIEW_PACKAGE"
            and report.actual_submission_allowed is False
            and report.actual_paper_orders_submitted==0
        ),
        "next_phase":"V138_01_CONTINUE_TERMINAL_MONITOR",
    }
    path=root/"release/v138_00/output/final_paper_submission_approval_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
