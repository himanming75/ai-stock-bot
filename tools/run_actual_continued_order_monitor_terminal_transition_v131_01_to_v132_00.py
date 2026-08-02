from datetime import datetime,timezone
from pathlib import Path
import argparse,json,os,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from alpaca_broker import AlpacaPaperClient,AlpacaPaperConfig,CredentialLoader,UrllibHttpTransport
from autonomous_paper_runtime.lifecycle_monitor import build_snapshot
from autonomous_paper_runtime.terminal_transition_gate import (
    ContinuedActualOrderMonitorTerminalTransitionGate,
)

ENABLE="AI_STOCK_BOT_ENABLE_ACTUAL_TERMINAL_TRANSITION_MONITOR"
CONFIRM="AI_STOCK_BOT_ACTUAL_TERMINAL_TRANSITION_CONFIRMATION"
TEXT="MONITOR ACTUAL ALPACA PAPER ORDER AND EVALUATE TERMINAL GET ONLY"


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
    p.add_argument("--client-order-id",default="single-60d3c5406e5226ae71d7")
    p.add_argument("--max-polls",type=int,default=3)
    p.add_argument("--poll-interval-seconds",type=float,default=5)
    a=p.parse_args()
    env=dict(os.environ)
    if env.get(ENABLE,"").upper()!="YES": raise SystemExit(f"{ENABLE}=YES is required")
    if env.get(CONFIRM,"")!=TEXT: raise SystemExit(f"{CONFIRM} must equal: {TEXT}")
    if not 1<=a.max_polls<=20: raise SystemExit("max-polls must be 1..20")
    if not 0<=a.poll_interval_seconds<=300: raise SystemExit("poll interval must be 0..300")

    key,secret=CredentialLoader().load(env)
    client=AlpacaPaperClient(
        config=AlpacaPaperConfig(network_read_enabled=True,network_write_enabled=False,max_retries=2),
        api_key=key,secret_key=secret,transport=UrllibHttpTransport()
    )
    root=Path(a.repository_root).resolve()
    gate=ContinuedActualOrderMonitorTerminalTransitionGate(
        lifecycle_ledger_path=root/"release/v132_00/actual/lifecycle.jsonl",
        completion_ledger_path=root/"release/v132_00/actual/completion.jsonl",
    )

    def poll(seq):
        o=client.get_order_by_client_id(a.client_order_id)
        positions=tuple(client.list_positions())
        account=client.get_account()
        order={
            "id":value(o,"order_id","id"),"client_order_id":value(o,"client_order_id"),
            "symbol":value(o,"symbol"),"side":value(o,"side"),"status":value(o,"status"),
            "quantity":value(o,"quantity","qty",default="0"),
            "filled_quantity":value(o,"filled_quantity","filled_qty",default="0"),
            "average_fill_price":value(o,"average_fill_price","filled_avg_price",default="0"),
        }
        pos=[{
            "symbol":value(x,"symbol"),
            "quantity":value(x,"quantity","qty",default="0"),
            "average_entry_price":value(x,"average_entry_price","average_price",default="0"),
        } for x in positions]
        acct={"cash":value(account,"cash",default="0"),"equity":value(account,"equity",default="0")}
        return build_snapshot(
            sequence=seq,observed_at=datetime.now(timezone.utc).isoformat(),
            order=order,positions=pos,account=acct
        )

    report=gate.run(
        poller=poll,max_polls=a.max_polls,
        poll_interval_seconds=a.poll_interval_seconds,
        network_requests_per_poll=3,
    )
    out={
        "stage_range":"V131.01-V132.00","status":"PASS",
        "implementation_type":"CONTINUED_ACTUAL_ORDER_MONITOR_TERMINAL_TRANSITION_GATE",
        "validation_mode":"ACTUAL_ALPACA_PAPER_GET_ONLY",
        "actual_credentials_used":True,"actual_external_network_used":True,
        **report.to_json_dict(),
        "next_phase":(
            "V132_01_TERMINAL_COMPLETION_COMMIT"
            if report.terminal_transition_observed
            else "V132_01_CONTINUE_ACTUAL_ORDER_MONITOR"
        ),
    }
    path=root/"release/v132_00/actual/actual_continued_monitor_terminal_transition_result.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0

if __name__=="__main__": raise SystemExit(main())
