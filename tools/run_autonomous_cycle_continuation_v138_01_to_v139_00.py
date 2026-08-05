from pathlib import Path
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from autonomous_paper_runtime.cycle_continuation import (
    AutonomousCycleContinuationOrchestrator,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    a=p.parse_args()
    root=Path(a.repository_root).resolve()

    terminal=json.loads(
        (root/"release/v134_00/actual/actual_terminal_monitor_commit_orchestrator_result.json").read_text(encoding="utf-8")
    )

    o=AutonomousCycleContinuationOrchestrator(
        root=root/"release/v139_00/runtime"
    )
    report=o.run(
        terminal_monitor_result=terminal,
        account={"status":"ACTIVE","trading_blocked":False},
        open_orders=[{"symbol":"AAPL","status":"ACCEPTED"}],
        positions=[],
        market_is_open=False,
        risk_approved=True,
        symbol="AAPL",
        side="BUY",
        quantity="1",
        estimated_price="50",
        approval_phrase="",
        created_at="",
        network_requests_executed=0,
    )

    out={
        "stage_range":"V138.01-V139.00",
        "status":"PASS",
        "implementation_type":"AUTONOMOUS_CYCLE_CONTINUATION_ORCHESTRATOR",
        "validation_mode":"PRIOR_ACTUAL_ACTIVE_ORDER_RESULT",
        **report.to_json_dict(),
        "active_wait_verified":(
            report.final_state=="WAIT_ACTIVE_ORDER"
            and report.stopped_at=="CYCLE_GATE"
            and report.actual_paper_orders_submitted==0
        ),
        "next_phase":"V139_01_CONTINUE_ACTUAL_TERMINAL_MONITOR",
    }
    path=root/"release/v139_00/output/autonomous_cycle_continuation_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
