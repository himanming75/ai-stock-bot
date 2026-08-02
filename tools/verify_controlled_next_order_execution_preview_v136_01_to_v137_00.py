from pathlib import Path
import argparse,json

def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
    r=json.loads((Path(a.repository_root).resolve()/"release/v137_00/output/controlled_next_order_execution_preview_result.json").read_text())
    checks={
        "status_pass":r["status"]=="PASS",
        "real_implementation":r["implementation_type"]=="CONTROLLED_NEXT_ORDER_EXECUTION_PREVIEW",
        "wait_cycle_token":r["state"]=="WAIT_CYCLE_TOKEN",
        "preview_not_created":r["preview_created"] is False,
        "payload_false":r["payload_valid"] is False,
        "approval_false":r["final_approval_required"] is False,
        "submission_false":r["actual_submission_allowed"] is False,
        "safe_mode_false":r["safe_mode_engaged"] is False,
        "reason_wait":r["reason"]=="cycle_not_ready",
        "wait_verified":r["wait_verified"] is True,
        "network_zero":r["network_requests_executed"]==0,
        "write_zero":r["write_requests_executed"]==0,
        "paper_zero":r["actual_paper_orders_submitted"]==0,
        "live_zero":r["live_orders_submitted"]==0,
    }
    failed=[k for k,v in checks.items() if not v]
    out={
        "stage_range":"V136.01-V137.00",
        "status":"PASS" if not failed else "FAIL",
        "checks":checks,
        "failed_checks":failed,
        "next_phase":r["next_phase"],
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not failed else 1

if __name__=="__main__": raise SystemExit(main())
