from pathlib import Path
import argparse,json,os,sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from autonomous_paper_runtime.next_order_preview import (
    ControlledNextOrderExecutionPreview,
)

ENABLE="AI_STOCK_BOT_ENABLE_ACTUAL_NEXT_ORDER_PREVIEW"
CONFIRM="AI_STOCK_BOT_ACTUAL_NEXT_ORDER_PREVIEW_CONFIRMATION"
TEXT="BUILD ONE LOCAL NEXT ORDER SUBMISSION PREVIEW ONLY"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    a=p.parse_args()

    env=dict(os.environ)
    if env.get(ENABLE,"").upper()!="YES":
        raise SystemExit(f"{ENABLE}=YES is required")
    if env.get(CONFIRM,"")!=TEXT:
        raise SystemExit(f"{CONFIRM} must equal: {TEXT}")

    root=Path(a.repository_root).resolve()
    source=root/"release/v136_00/actual/actual_controlled_next_order_cycle_result.json"
    cycle_result=json.loads(source.read_text(encoding="utf-8"))
    token_path=root/"release/v136_00/actual/next_order_cycle_token.json"
    token=json.loads(token_path.read_text(encoding="utf-8")) if token_path.exists() else None

    account_path=root/"release/v135_00/actual/actual_autonomous_next_order_readiness_result.json"
    readiness=json.loads(account_path.read_text(encoding="utf-8"))

    builder=ControlledNextOrderExecutionPreview(
        preview_path=root/"release/v137_00/actual/order_preview.json",
        risk_snapshot_path=root/"release/v137_00/actual/risk_snapshot.json",
        exposure_snapshot_path=root/"release/v137_00/actual/exposure_snapshot.json",
        approval_gate_path=root/"release/v137_00/actual/final_approval_gate.json",
    )
    report=builder.build(
        cycle_result=cycle_result,
        cycle_token=token,
        account_snapshot={
            "status":"ACTIVE" if readiness.get("account_active") else "INACTIVE",
            "trading_blocked":readiness.get("trading_blocked",False),
        },
        risk_snapshot={
            "approved":readiness.get("risk_approved",False),
            "source":"V135_ACTUAL_READINESS",
        },
        exposure_snapshot={
            "approved":(
                readiness.get("position_count",0) <= 3
                and float(readiness.get("total_market_value","0")) <= 1000
            ),
            "position_count":readiness.get("position_count",0),
            "total_market_value":readiness.get("total_market_value","0"),
        },
        created_at=datetime.now(timezone.utc).isoformat(),
        max_quantity="1",
        max_notional="100",
        network_requests_executed=0,
    )

    out={
        "stage_range":"V136.01-V137.00",
        "status":"PASS",
        "implementation_type":"CONTROLLED_NEXT_ORDER_EXECUTION_PREVIEW",
        "validation_mode":"ACTUAL_SAVED_STATE_LOCAL_PREVIEW_ONLY",
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        **report.to_json_dict(),
        "next_phase":(
            "V137_01_FINAL_PAPER_SUBMISSION_APPROVAL"
            if report.state.value=="READY_FOR_SUBMISSION_APPROVAL"
            else "V137_01_CONTINUE_TERMINAL_MONITOR"
        ),
    }
    path=root/"release/v137_00/actual/actual_controlled_next_order_execution_preview_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0

if __name__=="__main__": raise SystemExit(main())
