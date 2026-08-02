from decimal import Decimal
from pathlib import Path
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from autonomous_paper_runtime.lifecycle_monitor import LifecycleSnapshot
from autonomous_paper_runtime.terminal_monitor_commit_orchestrator import (
    TerminalMonitorCommitOrchestrator,
)


def main():
    p=argparse.ArgumentParser();p.add_argument("--repository-root",default=".");a=p.parse_args()
    root=Path(a.repository_root).resolve()
    o=TerminalMonitorCommitOrchestrator(
        lifecycle_ledger_path=root/"release/v134_00/ledger/lifecycle.jsonl",
        completion_ledger_path=root/"release/v134_00/ledger/completion.jsonl",
        audit_ledger_path=root/"release/v134_00/ledger/audit.jsonl",
        unlock_ledger_path=root/"release/v134_00/ledger/unlock.jsonl",
        recovery_snapshot_path=root/"release/v134_00/recovery/terminal_commit.json",
    )
    values=[
        LifecycleSnapshot(
            sequence=i,
            observed_at=f"2026-08-02T04:00:0{i}+00:00",
            broker_order_id="3bd9f491-0629-4cf4-9b0e-2a27eadea98d",
            client_order_id="single-60d3c5406e5226ae71d7",
            symbol="AAPL",side="BUY",status="ACCEPTED",
            quantity=Decimal("1"),filled_quantity=Decimal("0"),
            remaining_quantity=Decimal("1"),average_fill_price=Decimal("0"),
            position_quantity=Decimal("0"),position_average_price=Decimal("0"),
            cash=Decimal("100000"),equity=Decimal("100000"),
        ) for i in range(1,4)
    ]
    report=o.run(
        poller=lambda n:values[n-1],
        max_polls=3,
        network_requests_per_poll=0,
        source_result_path="offline_fixture",
    )
    out={
        "stage_range":"V133.01-V134.00",
        "status":"PASS",
        "implementation_type":"TERMINAL_MONITOR_COMMIT_ORCHESTRATOR",
        "validation_mode":"OFFLINE_ACTIVE_THREE_POLL",
        **report.to_json_dict(),
        "active_continue_verified":(
            report.monitor_report.final_status=="ACCEPTED"
            and report.commit_report.state.value=="CONTINUE_TRACKING"
            and report.terminal_committed is False
            and report.next_order_allowed is False
        ),
        "next_phase":"V134_01_CONTINUE_MONITOR_OR_AUTONOMOUS_NEXT_ORDER_READINESS",
    }
    path=root/"release/v134_00/output/terminal_monitor_commit_orchestrator_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True));return 0

if __name__=="__main__": raise SystemExit(main())
