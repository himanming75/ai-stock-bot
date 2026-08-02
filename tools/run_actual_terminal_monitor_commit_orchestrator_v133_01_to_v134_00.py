from datetime import datetime,timezone
from pathlib import Path
import argparse,json,os,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from alpaca_broker import AlpacaPaperClient,AlpacaPaperConfig,CredentialLoader,UrllibHttpTransport
from autonomous_paper_runtime.lifecycle_monitor import build_snapshot
from autonomous_paper_runtime.terminal_monitor_commit_orchestrator import (
    TerminalMonitorCommitOrchestrator,
)

ENABLE="AI_STOCK_BOT_ENABLE_ACTUAL_TERMINAL_MONITOR_COMMIT"
CONFIRM="AI_STOCK_BOT_ACTUAL_TERMINAL_MONITOR_COMMIT_CONFIRMATION"
TEXT="MONITOR ACTUAL ALPACA PAPER ORDER AND COMMIT TERMINAL LOCALLY GET ONLY"


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
    source_path=root/"release/v134_00/actual/last_snapshot.json"

    def poll(seq):
        order=client.get_order_by_client_id(a.client_order_id)
        positions=tuple(client.list_positions())
        account=client.get_account()
        symbol=str(value(order,"symbol",default="")).upper()
        order_data={
            "id":str(value(order,"order_id","id")),
            "client_order_id":str(value(order,"client_order_id")),
            "symbol":symbol,
            "side":str(value(order,"side")),
            "status":str(value(order,"status")),
            "quantity":str(value(order,"quantity","qty",default="0")),
            "filled_quantity":str(value(order,"filled_quantity","filled_qty",default="0")),
            "average_fill_price":str(value(order,"average_fill_price","filled_avg_price",default="0")),
        }
        position_data=[{
            "symbol":str(value(x,"symbol",default="")),
            "quantity":str(value(x,"quantity","qty",default="0")),
            "average_entry_price":str(value(x,"average_entry_price","average_price",default="0")),
        } for x in positions]
        account_data={
            "cash":str(value(account,"cash",default="0")),
            "equity":str(value(account,"equity",default="0")),
        }
        snapshot=build_snapshot(
            sequence=seq,
            observed_at=datetime.now(timezone.utc).isoformat(),
            order=order_data,
            positions=position_data,
            account=account_data,
        )
        source_path.parent.mkdir(parents=True,exist_ok=True)
        source_path.write_text(
            json.dumps(snapshot.to_json_dict(),indent=2,sort_keys=True)+"\n",
            encoding="utf-8",
        )
        return snapshot

    o=TerminalMonitorCommitOrchestrator(
        lifecycle_ledger_path=root/"release/v134_00/actual/lifecycle.jsonl",
        completion_ledger_path=root/"release/v134_00/actual/completion.jsonl",
        audit_ledger_path=root/"release/v134_00/actual/audit.jsonl",
        unlock_ledger_path=root/"release/v134_00/actual/unlock.jsonl",
        recovery_snapshot_path=root/"release/v134_00/actual/terminal_commit_recovery.json",
    )
    report=o.run(
        poller=poll,
        max_polls=a.max_polls,
        poll_interval_seconds=a.poll_interval_seconds,
        network_requests_per_poll=3,
        source_result_path=str(source_path),
    )
    out={
        "stage_range":"V133.01-V134.00",
        "status":"PASS",
        "implementation_type":"TERMINAL_MONITOR_COMMIT_ORCHESTRATOR",
        "validation_mode":"ACTUAL_ALPACA_PAPER_GET_ONLY_LOCAL_COMMIT",
        "actual_credentials_used":True,
        "actual_external_network_used":True,
        **report.to_json_dict(),
        "next_phase":(
            "V134_01_AUTONOMOUS_NEXT_ORDER_READINESS"
            if report.terminal_committed
            else "V134_01_CONTINUE_ACTUAL_TERMINAL_MONITOR"
        ),
    }
    result_path=root/"release/v134_00/actual/actual_terminal_monitor_commit_orchestrator_result.json"
    result_path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    print(f"RESULT_FILE={result_path}")
    return 0

if __name__=="__main__": raise SystemExit(main())
