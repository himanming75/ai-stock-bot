from datetime import datetime,timezone
from pathlib import Path
import argparse,json,os,sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from alpaca_broker import AlpacaPaperClient,AlpacaPaperConfig,CredentialLoader,UrllibHttpTransport
from autonomous_paper_runtime.terminal_commit import JsonlLedger,TerminalCompletionCommitter

ENABLE="AI_STOCK_BOT_ENABLE_ACTUAL_TERMINAL_COMMIT_READ"
CONFIRM="AI_STOCK_BOT_ACTUAL_TERMINAL_COMMIT_CONFIRMATION"
TEXT="READ ACTUAL ALPACA PAPER TERMINAL STATE AND COMMIT LOCALLY GET ONLY"


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
    a=p.parse_args()

    env=dict(os.environ)
    if env.get(ENABLE,"").upper()!="YES": raise SystemExit(f"{ENABLE}=YES is required")
    if env.get(CONFIRM,"")!=TEXT: raise SystemExit(f"{CONFIRM} must equal: {TEXT}")

    key,secret=CredentialLoader().load(env)
    client=AlpacaPaperClient(
        config=AlpacaPaperConfig(network_read_enabled=True,network_write_enabled=False,max_retries=2),
        api_key=key,secret_key=secret,transport=UrllibHttpTransport()
    )

    order=client.get_order_by_client_id(a.client_order_id)
    positions=tuple(client.list_positions())
    account=client.get_account()

    symbol=str(value(order,"symbol",default="")).upper()
    position=next((x for x in positions if str(value(x,"symbol",default="")).upper()==symbol),None)

    root=Path(a.repository_root).resolve()
    committer=TerminalCompletionCommitter(
        completion_ledger=JsonlLedger(root/"release/v133_00/actual/completion.jsonl"),
        audit_ledger=JsonlLedger(root/"release/v133_00/actual/audit.jsonl"),
        unlock_ledger=JsonlLedger(root/"release/v133_00/actual/unlock.jsonl"),
        recovery_snapshot_path=root/"release/v133_00/actual/terminal_commit_recovery.json",
    )
    source_path=root/"release/v133_00/actual/actual_terminal_state_snapshot.json"
    snapshot={
        "client_order_id":value(order,"client_order_id"),
        "broker_order_id":value(order,"order_id","id"),
        "symbol":symbol,
        "side":value(order,"side"),
        "final_status":value(order,"status"),
        "quantity":str(value(order,"quantity","qty",default="0")),
        "filled_quantity":str(value(order,"filled_quantity","filled_qty",default="0")),
        "remaining_quantity":str(
            max(
                __import__("decimal").Decimal("0"),
                __import__("decimal").Decimal(str(value(order,"quantity","qty",default="0")))
                - __import__("decimal").Decimal(str(value(order,"filled_quantity","filled_qty",default="0")))
            )
        ),
        "average_fill_price":str(value(order,"average_fill_price","filled_avg_price",default="0")),
        "position_quantity":str(value(position,"quantity","qty",default="0")) if position else "0",
        "cash":str(value(account,"cash",default="0")),
        "equity":str(value(account,"equity",default="0")),
    }
    source_path.parent.mkdir(parents=True,exist_ok=True)
    source_path.write_text(json.dumps(snapshot,indent=2,sort_keys=True)+"\n",encoding="utf-8")

    report=committer.commit(
        terminal_result=snapshot,
        source_result_path=str(source_path),
        completed_at=datetime.now(timezone.utc).isoformat(),
        network_requests_executed=3,
    )
    out={
        "stage_range":"V132.01-V133.00",
        "status":"PASS",
        "implementation_type":"TERMINAL_COMPLETION_COMMIT",
        "validation_mode":"ACTUAL_ALPACA_PAPER_GET_ONLY_LOCAL_COMMIT",
        "actual_credentials_used":True,
        "actual_external_network_used":True,
        **report.to_json_dict(),
        "next_phase":(
            "V133_01_AUTONOMOUS_NEXT_ORDER_READINESS"
            if report.committed or report.duplicate_commit
            else "V133_01_CONTINUE_TERMINAL_MONITOR"
        ),
    }
    path=root/"release/v133_00/actual/actual_terminal_completion_commit_result.json"
    path.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2,sort_keys=True))
    print(f"RESULT_FILE={path}")
    return 0

if __name__=="__main__": raise SystemExit(main())

