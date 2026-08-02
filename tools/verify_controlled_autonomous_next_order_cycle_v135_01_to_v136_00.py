from pathlib import Path
import argparse,json

def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
    r=json.loads((Path(a.repository_root).resolve()/"release/v136_00/output/controlled_autonomous_next_order_cycle_result.json").read_text())
    checks={
        "status_pass":r["status"]=="PASS",
        "real_implementation":r["implementation_type"]=="CONTROLLED_AUTONOMOUS_NEXT_ORDER_CYCLE",
        "wait_active":r["state"]=="WAIT_ACTIVE_ORDER",
        "cycle_not_created":r["cycle_created"] is False,
        "not_duplicate":r["duplicate_cycle"] is False,
        "preview_false":r["preview_ready"] is False,
        "new_order_blocked":r["next_order_allowed"] is False,
        "safe_mode_false":r["safe_mode_engaged"] is False,
        "reason_active":r["reason"]=="active_order_present",
        "token_not_written":r["cycle_token_written"] is False,
        "active_verified":r["active_wait_verified"] is True,
        "network_zero":r["network_requests_executed"]==0,
        "write_zero":r["write_requests_executed"]==0,
        "paper_zero":r["actual_paper_orders_submitted"]==0,
        "live_zero":r["live_orders_submitted"]==0,
    }
    failed=[k for k,v in checks.items() if not v]
    out={
        "stage_range":"V135.01-V136.00",
        "status":"PASS" if not failed else "FAIL",
        "checks":checks,
        "failed_checks":failed,
        "next_phase":r["next_phase"],
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not failed else 1

if __name__=="__main__": raise SystemExit(main())
