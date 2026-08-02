from pathlib import Path
import argparse,json

def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
    r=json.loads((Path(a.repository_root).resolve()/"release/v132_00/output/continued_monitor_terminal_transition_result.json").read_text())
    m=r["monitor_report"];c=r["completion_report"]
    checks={
        "status_pass":r["status"]=="PASS",
        "real_implementation":r["implementation_type"]=="CONTINUED_ACTUAL_ORDER_MONITOR_TERMINAL_TRANSITION_GATE",
        "three_polls":m["poll_count"]==3,
        "accepted":m["final_status"]=="ACCEPTED",
        "not_terminal":r["terminal_transition_observed"] is False,
        "active_locked":c["state"]=="LOCKED_ACTIVE_ORDER",
        "new_order_blocked":r["new_order_allowed"] is False,
        "safe_mode_false":r["safe_mode_engaged"] is False,
        "ledger_not_written":c["ledger_entry_written"] is False,
        "write_zero":c["write_requests_executed"]==0,
        "paper_zero":c["actual_paper_orders_submitted"]==0,
        "live_zero":c["live_orders_submitted"]==0,
        "guard":r["active_lock_verified"] is True,
    }
    failed=[k for k,v in checks.items() if not v]
    out={"stage_range":"V131.01-V132.00","status":"PASS" if not failed else "FAIL","checks":checks,"failed_checks":failed,"next_phase":r["next_phase"]}
    print(json.dumps(out,indent=2,sort_keys=True));return 0 if not failed else 1

if __name__=="__main__": raise SystemExit(main())
