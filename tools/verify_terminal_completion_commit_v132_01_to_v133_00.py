from pathlib import Path
import argparse,json

def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
    r=json.loads((Path(a.repository_root).resolve()/"release/v133_00/output/terminal_completion_commit_result.json").read_text())
    checks={
        "status_pass":r["status"]=="PASS",
        "real_implementation":r["implementation_type"]=="TERMINAL_COMPLETION_COMMIT",
        "continue_tracking":r["state"]=="CONTINUE_TRACKING",
        "terminal_false":r["terminal"] is False,
        "not_committed":r["committed"] is False,
        "not_duplicate":r["duplicate_commit"] is False,
        "new_order_blocked":r["next_order_allowed"] is False,
        "safe_mode_false":r["safe_mode_engaged"] is False,
        "completion_not_written":r["completion_ledger_written"] is False,
        "audit_not_written":r["audit_ledger_written"] is False,
        "unlock_not_written":r["unlock_ledger_written"] is False,
        "recovery_not_written":r["recovery_snapshot_written"] is False,
        "active_verified":r["active_continue_verified"] is True,
        "network_zero":r["network_requests_executed"]==0,
        "write_zero":r["write_requests_executed"]==0,
        "paper_zero":r["actual_paper_orders_submitted"]==0,
        "live_zero":r["live_orders_submitted"]==0,
    }
    failed=[k for k,v in checks.items() if not v]
    out={"stage_range":"V132.01-V133.00","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,"next_phase":r["next_phase"]}
    print(json.dumps(out,indent=2,sort_keys=True));return 0 if not failed else 1

if __name__=="__main__": raise SystemExit(main())
