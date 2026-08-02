from pathlib import Path
import argparse,json

def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
    r=json.loads((Path(a.repository_root).resolve()/"release/v134_00/output/terminal_monitor_commit_orchestrator_result.json").read_text())
    m=r["monitor_report"];c=r["commit_report"]
    checks={
        "status_pass":r["status"]=="PASS",
        "real_implementation":r["implementation_type"]=="TERMINAL_MONITOR_COMMIT_ORCHESTRATOR",
        "three_polls":m["poll_count"]==3,
        "accepted":m["final_status"]=="ACCEPTED",
        "terminal_false":r["terminal_observed"] is False,
        "commit_not_attempted":r["commit_attempted"] is False,
        "not_committed":r["terminal_committed"] is False,
        "continue_tracking":c["state"]=="CONTINUE_TRACKING",
        "new_order_blocked":r["next_order_allowed"] is False,
        "safe_mode_false":r["safe_mode_engaged"] is False,
        "completion_not_written":c["completion_ledger_written"] is False,
        "audit_not_written":c["audit_ledger_written"] is False,
        "unlock_not_written":c["unlock_ledger_written"] is False,
        "write_zero":c["write_requests_executed"]==0,
        "paper_zero":c["actual_paper_orders_submitted"]==0,
        "live_zero":c["live_orders_submitted"]==0,
        "active_verified":r["active_continue_verified"] is True,
    }
    failed=[k for k,v in checks.items() if not v]
    out={"stage_range":"V133.01-V134.00","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,"next_phase":r["next_phase"]}
    print(json.dumps(out,indent=2,sort_keys=True));return 0 if not failed else 1

if __name__=="__main__": raise SystemExit(main())
