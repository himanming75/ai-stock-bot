from decimal import Decimal
from pathlib import Path
import argparse,json,os,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from alpaca_broker import AlpacaPaperClient,AlpacaPaperConfig,CredentialLoader,UrllibHttpTransport
from autonomous_paper_runtime.next_order_readiness import (
    AutonomousNextOrderReadinessGate,
)

ENABLE="AI_STOCK_BOT_ENABLE_ACTUAL_NEXT_ORDER_READINESS"
CONFIRM="AI_STOCK_BOT_ACTUAL_NEXT_ORDER_READINESS_CONFIRMATION"
TEXT="READ ACTUAL ALPACA PAPER ACCOUNT FOR NEXT ORDER READINESS GET ONLY"


def value(item,*names,default=""):
    for name in names:
        v=getattr(item,name,None)
        if v not in (None,""):
            return getattr(v,"value",v)
    for raw_name in ("raw","_raw","data","_data"):
        raw=getattr(item,raw_name,None)
        if isinstance(raw,dict):
            for name in names:
                v=raw.get(name)
                if v not in (None,""): return v
    return default


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repository-root",default=".")
    p.add_argument("--max-positions",type=int,default=3)
    p.add_argument("--max-total-market-value",default="1000")
    p.add_argument("--risk-approved",default="YES")
    a=p.parse_args()

    env=dict(os.environ)
    if env.get(ENABLE,"").upper()!="YES": raise SystemExit(f"{ENABLE}=YES is required")
    if env.get(CONFIRM,"")!=TEXT: raise SystemExit(f"{CONFIRM} must equal: {TEXT}")

    key,secret=CredentialLoader().load(env)
    client=AlpacaPaperClient(
        config=AlpacaPaperConfig(
            network_read_enabled=True,
            network_write_enabled=False,
            max_retries=2,
        ),
        api_key=key,
        secret_key=secret,
        transport=UrllibHttpTransport(),
    )

    root=Path(a.repository_root).resolve()
    terminal_path=root/"release/v134_00/actual/actual_terminal_monitor_commit_orchestrator_result.json"
    terminal=json.loads(terminal_path.read_text(encoding="utf-8"))

    account=client.get_account()
    orders=tuple(client.list_orders(status="open"))
    positions=tuple(client.list_positions())
    clock=client.get_clock()

    account_data={
        "status":str(value(account,"status",default="")),
        "trading_blocked":value(account,"trading_blocked",default=False),
    }
    order_data=[{
        "client_order_id":str(value(x,"client_order_id",default="")),
        "symbol":str(value(x,"symbol",default="")),
        "status":str(value(x,"status",default="")),
    } for x in orders]
    position_data=[{
        "symbol":str(value(x,"symbol",default="")),
        "market_value":str(value(x,"market_value",default="0")),
        "quantity":str(value(x,"quantity","qty",default="0")),
    } for x in positions]

    gate=AutonomousNextOrderReadinessGate(
        readiness_snapshot_path=root/"release/v135_00/actual/next_order_readiness.json"
    )
    report=gate.evaluate(
        terminal_monitor_result=terminal,
        account=account_data,
        open_orders=order_data,
        positions=position_data,
        market_is_open=bool(value(clock,"is_open",default=False)),
        risk_approved=a.risk_approved.strip().upper()=="YES",
        max_positions=a.max_positions,
        max_total_market_value=Decimal(a.max_total_market_value),
        network_requests_executed=4,
    )

    out={
        "stage_range":"V134.01-V135.00",
        "status":"PASS",
        "implementation_type":"AUTONOMOUS_NEXT_ORDER_READINESS_GATE",
        "validation_mode":"ACTUAL_ALPACA_PAPER_GET_ONLY",
        "actual_credentials_used":True,
        "actual_external_network_used":True,
        **report.to_json_dict(),
        "next_phase":(
            "V135_01_CONTROLLED_AUTONOMOUS_NEXT_ORDER_CYCLE"
            if report.ready
            else "V135_01_CONTINUE_TERMINAL_MONITOR"
        ),
    }
    path=root/"release/v135_00/actual/actual_autonomous_next_order_readiness_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0

if __name__=="__main__": raise SystemExit(main())
