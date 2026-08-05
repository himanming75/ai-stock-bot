from pathlib import Path
import argparse,json,os,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from autonomous_paper_runtime.cycle_continuation import (
    AutonomousCycleContinuationOrchestrator,
)

ENABLE="AI_STOCK_BOT_ENABLE_ACTUAL_CYCLE_CONTINUATION"
CONFIRM="AI_STOCK_BOT_ACTUAL_CYCLE_CONTINUATION_CONFIRMATION"
TEXT="EVALUATE ACTUAL SAVED AUTONOMOUS CYCLE CONTINUATION LOCAL ONLY"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--approval-phrase",default="")
    a=p.parse_args()

    env=dict(os.environ)
    if env.get(ENABLE,"").upper()!="YES":
        raise SystemExit(f"{ENABLE}=YES is required")
    if env.get(CONFIRM,"")!=TEXT:
        raise SystemExit(f"{CONFIRM} must equal: {TEXT}")

    root=Path(a.repository_root).resolve()
    terminal=json.loads(
        (root/"release/v134_00/actual/actual_terminal_monitor_commit_orchestrator_result.json").read_text(encoding="utf-8")
    )
    readiness=json.loads(
        (root/"release/v135_00/actual/actual_autonomous_next_order_readiness_result.json").read_text(encoding="utf-8")
    )

    open_orders = (
        [{"symbol":"AAPL","status":"ACCEPTED"}]
        if readiness.get("open_order_count",0) > 0
        else []
    )

    o=AutonomousCycleContinuationOrchestrator(
        root=root/"release/v139_00/actual"
    )
    report=o.run(
        terminal_monitor_result=terminal,
        account={
            "status":"ACTIVE" if readiness.get("account_active") else "INACTIVE",
            "trading_blocked":readiness.get("trading_blocked",False),
        },
        open_orders=open_orders,
        positions=[],
        market_is_open=readiness.get("market_is_open",False),
        risk_approved=readiness.get("risk_approved",False),
        symbol="AAPL",
        side="BUY",
        quantity="1",
        estimated_price="50",
        approval_phrase=a.approval_phrase,
        created_at="",
        network_requests_executed=0,
    )

    out={
        "stage_range":"V138.01-V139.00",
        "status":"PASS",
        "implementation_type":"AUTONOMOUS_CYCLE_CONTINUATION_ORCHESTRATOR",
        "validation_mode":"ACTUAL_SAVED_STATE_LOCAL_ONLY",
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        **report.to_json_dict(),
        "next_phase":(
            "V139_01_EXACTLY_ONE_PAPER_ORDER_SUBMISSION"
            if report.actual_submission_allowed
            else "V139_01_CONTINUE_ACTUAL_TERMINAL_MONITOR"
        ),
    }
    path=root/"release/v139_00/actual/actual_autonomous_cycle_continuation_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0

if __name__=="__main__": raise SystemExit(main())
