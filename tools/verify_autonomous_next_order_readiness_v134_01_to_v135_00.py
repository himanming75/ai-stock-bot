from pathlib import Path
import argparse,json

def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
    r=json.loads((Path(a.repository_root).resolve()/"release/v135_00/output/autonomous_next_order_readiness_result.json").read_text())
    checks={
        "status_pass":r["status"]=="PASS",
        "real_implementation":r["implementation_type"]=="AUTONOMOUS_NEXT_ORDER_READINESS_GATE",
        "blocked_active":r["state"]=="BLOCKED_ACTIVE_ORDER",
        "ready_false":r["ready"] is False,
        "new_order_blocked":r["next_order_allowed"] is False,
        "active_order_true":r["active_order_present"] is True,
        "open_order_one":r["open_order_count"]==1,
        "account_active":r["account_active"] is True,
        "trading_not_blocked":r["trading_blocked"] is False,
        "market_open":r["market_is_open"] is True,
        "risk_approved":r["risk_approved"] is True,
        "snapshot_written":r["readiness_snapshot_written"] is True,
        "guard_verified":r["active_order_block_verified"] is True,
        "network_zero":r["network_requests_executed"]==0,
        "write_zero":r["write_requests_executed"]==0,
        "paper_zero":r["actual_paper_orders_submitted"]==0,
        "live_zero":r["live_orders_submitted"]==0,
    }
    failed=[k for k,v in checks.items() if not v]
    out={
        "stage_range":"V134.01-V135.00",
        "status":"PASS" if not failed else "FAIL",
        "checks":checks,
        "failed_checks":failed,
        "next_phase":r["next_phase"],
    }
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not failed else 1

if __name__=="__main__": raise SystemExit(main())
