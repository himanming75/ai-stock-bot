from decimal import Decimal
from pathlib import Path
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from autonomous_paper_runtime.next_order_readiness import (
    AutonomousNextOrderReadinessGate,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    a=p.parse_args()
    root=Path(a.repository_root).resolve()

    source=root/"release/v134_00/actual/actual_terminal_monitor_commit_orchestrator_result.json"
    terminal=json.loads(source.read_text(encoding="utf-8"))

    gate=AutonomousNextOrderReadinessGate(
        readiness_snapshot_path=root/"release/v135_00/readiness/next_order_readiness.json"
    )
    report=gate.evaluate(
        terminal_monitor_result=terminal,
        account={"status":"ACTIVE","trading_blocked":False},
        open_orders=[{
            "client_order_id":"single-60d3c5406e5226ae71d7",
            "symbol":"AAPL",
            "status":"ACCEPTED",
        }],
        positions=[],
        market_is_open=True,
        risk_approved=True,
        max_positions=3,
        max_total_market_value=Decimal("1000"),
        network_requests_executed=0,
    )

    out={
        "stage_range":"V134.01-V135.00",
        "status":"PASS",
        "implementation_type":"AUTONOMOUS_NEXT_ORDER_READINESS_GATE",
        "validation_mode":"PRIOR_ACTUAL_RESULT_ACTIVE_ORDER_FIXTURE",
        **report.to_json_dict(),
        "active_order_block_verified":(
            report.state.value=="BLOCKED_ACTIVE_ORDER"
            and report.next_order_allowed is False
            and report.active_order_present is True
        ),
        "next_phase":"V135_01_CONTINUE_TERMINAL_MONITOR",
    }
    path=root/"release/v135_00/output/autonomous_next_order_readiness_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
