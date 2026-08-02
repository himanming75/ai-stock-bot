from pathlib import Path
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from autonomous_paper_runtime.terminal_commit import (
    JsonlLedger,
    TerminalCompletionCommitter,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    a=p.parse_args()
    root=Path(a.repository_root).resolve()

    source=root/"release/v132_00/actual/actual_continued_monitor_terminal_transition_result.json"
    data=json.loads(source.read_text(encoding="utf-8"))
    monitor=data["monitor_report"]
    final=monitor["snapshots"][-1]

    committer=TerminalCompletionCommitter(
        completion_ledger=JsonlLedger(root/"release/v133_00/ledger/completion.jsonl"),
        audit_ledger=JsonlLedger(root/"release/v133_00/ledger/audit.jsonl"),
        unlock_ledger=JsonlLedger(root/"release/v133_00/ledger/unlock.jsonl"),
        recovery_snapshot_path=root/"release/v133_00/recovery/terminal_commit_recovery.json",
    )
    report=committer.commit(
        terminal_result={
            "client_order_id":final.get("client_order_id",""),
            "broker_order_id":final.get("broker_order_id",""),
            "symbol":final.get("symbol",""),
            "side":final.get("side",""),
            "final_status":monitor.get("final_status",""),
            "quantity":final.get("quantity","0"),
            "filled_quantity":monitor.get("final_filled_quantity","0"),
            "remaining_quantity":monitor.get("final_remaining_quantity","0"),
            "average_fill_price":final.get("average_fill_price","0"),
            "position_quantity":monitor.get("final_position_quantity","0"),
            "cash":final.get("cash","0"),
            "equity":final.get("equity","0"),
        },
        source_result_path=str(source),
        completed_at="",
        network_requests_executed=0,
    )

    out={
        "stage_range":"V132.01-V133.00",
        "status":"PASS",
        "implementation_type":"TERMINAL_COMPLETION_COMMIT",
        "validation_mode":"PRIOR_ACTUAL_TERMINAL_TRANSITION_RESULT",
        **report.to_json_dict(),
        "active_continue_verified":(
            report.state.value=="CONTINUE_TRACKING"
            and report.committed is False
            and report.next_order_allowed is False
        ),
        "next_phase":"V133_01_CONTINUE_TERMINAL_MONITOR",
    }
    path=root/"release/v133_00/output/terminal_completion_commit_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
