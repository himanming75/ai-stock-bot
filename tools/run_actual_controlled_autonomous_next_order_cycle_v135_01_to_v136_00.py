from pathlib import Path
import argparse,json,os,sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from autonomous_paper_runtime.next_order_cycle import (
    ControlledAutonomousNextOrderCycle,
)

ENABLE="AI_STOCK_BOT_ENABLE_ACTUAL_NEXT_ORDER_CYCLE"
CONFIRM="AI_STOCK_BOT_ACTUAL_NEXT_ORDER_CYCLE_CONFIRMATION"
TEXT="EVALUATE ACTUAL NEXT ORDER READINESS AND CREATE ONE LOCAL CYCLE TOKEN ONLY"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--symbol",default="AAPL")
    p.add_argument("--side",default="BUY")
    p.add_argument("--quantity",default="1")
    p.add_argument("--estimated-price",default="50")
    p.add_argument("--max-quantity",default="1")
    p.add_argument("--max-notional",default="100")
    a=p.parse_args()

    env=dict(os.environ)
    if env.get(ENABLE,"").upper()!="YES":
        raise SystemExit(f"{ENABLE}=YES is required")
    if env.get(CONFIRM,"")!=TEXT:
        raise SystemExit(f"{CONFIRM} must equal: {TEXT}")

    root=Path(a.repository_root).resolve()
    source=root/"release/v135_00/actual/actual_autonomous_next_order_readiness_result.json"
    readiness=json.loads(source.read_text(encoding="utf-8"))

    cycle=ControlledAutonomousNextOrderCycle(
        cycle_token_path=root/"release/v136_00/actual/next_order_cycle_token.json"
    )
    report=cycle.evaluate(
        readiness_result=readiness,
        symbol=a.symbol,
        side=a.side,
        quantity=a.quantity,
        estimated_price=a.estimated_price,
        created_at=datetime.now(timezone.utc).isoformat(),
        max_quantity=a.max_quantity,
        max_notional=a.max_notional,
        network_requests_executed=0,
    )

    out={
        "stage_range":"V135.01-V136.00",
        "status":"PASS",
        "implementation_type":"CONTROLLED_AUTONOMOUS_NEXT_ORDER_CYCLE",
        "validation_mode":"ACTUAL_READINESS_LOCAL_CYCLE_TOKEN_ONLY",
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        **report.to_json_dict(),
        "next_phase":(
            "V136_01_CONTROLLED_NEXT_ORDER_EXECUTION_PREVIEW"
            if report.preview_ready
            else "V136_01_CONTINUE_TERMINAL_MONITOR"
        ),
    }
    path=root/"release/v136_00/actual/actual_controlled_next_order_cycle_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0

if __name__=="__main__": raise SystemExit(main())
