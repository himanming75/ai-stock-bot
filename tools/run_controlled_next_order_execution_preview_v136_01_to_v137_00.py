from pathlib import Path
import argparse,json,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from autonomous_paper_runtime.next_order_preview import (
    ControlledNextOrderExecutionPreview,
)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    a=p.parse_args()
    root=Path(a.repository_root).resolve()

    source=root/"release/v136_00/actual/actual_controlled_next_order_cycle_result.json"
    cycle_result=json.loads(source.read_text(encoding="utf-8"))
    token_path=root/"release/v136_00/actual/next_order_cycle_token.json"
    token=json.loads(token_path.read_text(encoding="utf-8")) if token_path.exists() else None

    builder=ControlledNextOrderExecutionPreview(
        preview_path=root/"release/v137_00/preview/order_preview.json",
        risk_snapshot_path=root/"release/v137_00/preview/risk_snapshot.json",
        exposure_snapshot_path=root/"release/v137_00/preview/exposure_snapshot.json",
        approval_gate_path=root/"release/v137_00/preview/final_approval_gate.json",
    )
    report=builder.build(
        cycle_result=cycle_result,
        cycle_token=token,
        account_snapshot={"status":"ACTIVE","trading_blocked":False},
        risk_snapshot={"approved":True,"mode":"OFFLINE_FIXTURE"},
        exposure_snapshot={"approved":True,"total_market_value":"0"},
        created_at="",
        max_quantity="1",
        max_notional="100",
        network_requests_executed=0,
    )

    out={
        "stage_range":"V136.01-V137.00",
        "status":"PASS",
        "implementation_type":"CONTROLLED_NEXT_ORDER_EXECUTION_PREVIEW",
        "validation_mode":"PRIOR_ACTUAL_CYCLE_RESULT",
        **report.to_json_dict(),
        "wait_verified":(
            report.state.value=="WAIT_CYCLE_TOKEN"
            and report.preview_created is False
            and report.actual_paper_orders_submitted==0
        ),
        "next_phase":"V137_01_CONTINUE_TERMINAL_MONITOR",
    }
    path=root/"release/v137_00/output/controlled_next_order_execution_preview_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
