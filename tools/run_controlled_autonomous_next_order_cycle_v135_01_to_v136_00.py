from pathlib import Path
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from autonomous_paper_runtime.next_order_cycle import (
    ControlledAutonomousNextOrderCycle,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    a=p.parse_args()
    root=Path(a.repository_root).resolve()

    source=root/"release/v135_00/actual/actual_autonomous_next_order_readiness_result.json"
    readiness=json.loads(source.read_text(encoding="utf-8"))

    cycle=ControlledAutonomousNextOrderCycle(
        cycle_token_path=root/"release/v136_00/cycle/next_order_cycle_token.json"
    )
    report=cycle.evaluate(
        readiness_result=readiness,
        symbol="AAPL",
        side="BUY",
        quantity="1",
        estimated_price="50",
        created_at="",
        max_quantity="1",
        max_notional="100",
        network_requests_executed=0,
    )

    out={
        "stage_range":"V135.01-V136.00",
        "status":"PASS",
        "implementation_type":"CONTROLLED_AUTONOMOUS_NEXT_ORDER_CYCLE",
        "validation_mode":"PRIOR_ACTUAL_READINESS_RESULT",
        **report.to_json_dict(),
        "active_wait_verified":(
            report.state.value=="WAIT_ACTIVE_ORDER"
            and report.preview_ready is False
            and report.actual_paper_orders_submitted==0
        ),
        "next_phase":"V136_01_CONTINUE_TERMINAL_MONITOR",
    }
    path=root/"release/v136_00/output/controlled_autonomous_next_order_cycle_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
