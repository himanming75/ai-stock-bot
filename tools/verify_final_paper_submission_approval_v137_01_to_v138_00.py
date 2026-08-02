from pathlib import Path
import argparse,json

def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
    r=json.loads((Path(a.repository_root).resolve()/"release/v138_00/output/final_paper_submission_approval_result.json").read_text())
    checks={
        "status_pass":r["status"]=="PASS",
        "real_implementation":r["implementation_type"]=="FINAL_PAPER_SUBMISSION_APPROVAL_GATE",
        "wait_preview":r["state"]=="WAIT_PREVIEW_PACKAGE",
        "preview_false":r["preview_verified"] is False,
        "approval_required_false":r["final_approval_required"] is False,
        "human_false":r["human_approval_verified"] is False,
        "token_false":r["approval_token_created"] is False,
        "submission_false":r["actual_submission_allowed"] is False,
        "safe_mode_false":r["safe_mode_engaged"] is False,
        "reason_wait":r["reason"]=="preview_package_not_ready",
        "wait_verified":r["wait_verified"] is True,
        "network_zero":r["network_requests_executed"]==0,
        "write_zero":r["write_requests_executed"]==0,
        "paper_zero":r["actual_paper_orders_submitted"]==0,
        "live_zero":r["live_orders_submitted"]==0,
    }
    failed=[k for k,v in checks.items() if not v]
    out={
        "stage_range":"V137.01-V138.00",
        "status":"PASS" if not failed else "FAIL",
        "checks":checks,
        "failed_checks":failed,
        "next_phase":r["next_phase"],
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not failed else 1

if __name__=="__main__": raise SystemExit(main())
