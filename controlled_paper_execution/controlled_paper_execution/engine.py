from datetime import datetime,timezone
from pathlib import Path
from .credentials import load as load_credentials
from .client import AlpacaPaperClient
from .gates import evaluate
from .io import read_json,write_json,append_jsonl
ACTUAL=Path("release/v361_01_to_v370_64/actual")
def _counter(path):
    today=datetime.now(timezone.utc).date().isoformat()
    if not path.exists(): return {"date":today,"submitted_orders":0,"proposal_hashes":[]}
    v=read_json(path)
    return v if v.get("date")==today else {"date":today,"submitted_orders":0,"proposal_hashes":[]}
def _payload(p):
    o=p["proposal"]; return {"symbol":str(o["symbol"]).upper(),"side":str(o["side"]).lower(),"type":"market","time_in_force":"day","notional":str(round(float(o["estimated_notional"]),2)),"client_order_id":f"AISB-V370-{p['proposal_hash'][:20]}"}
def execute(root,proposal,policy,enable_phrase="",allow_network=False,client=None):
    root=Path(root); creds=load_credentials(); cp=root/ACTUAL/"daily_submission_counter.json"; c=_counter(cp)
    clock=account=None; orders=[]; network=False
    if allow_network and creds["ready"]:
        client=client or AlpacaPaperClient(creds["api_key"],creds["secret_key"])
        clock=client.get_clock(); account=client.get_account(); orders=client.get_orders("open"); network=True
    gate=evaluate(proposal,policy,creds,enable_phrase,clock,account,orders,c)
    submitted=0; resp=None; state="CONTROLLED_PAPER_EXECUTION_BLOCKED"
    if gate["allowed"] and allow_network:
        resp=client.submit_order(_payload(proposal)); submitted=1; state="CONTROLLED_PAPER_ORDER_SUBMITTED"
        c["submitted_orders"]=int(c.get("submitted_orders",0))+1;c.setdefault("proposal_hashes",[]).append(proposal["proposal_hash"]);write_json(cp,c)
    result={"stage":"V370.64","state":state,"status":"PASS","executed_at":datetime.now(timezone.utc).isoformat(),
      "network_used":network,"allow_network":allow_network,"gate":gate,"submission_payload":_payload(proposal) if gate["allowed"] else None,
      "order_response":resp,"proposal_hash":proposal.get("proposal_hash"),"paper_endpoint_only":True,
      "paper_submission_enabled":bool(policy.get("paper_submission_enabled")),"live_submission_enabled":False,"live_endpoint_enabled":False,
      "actual_paper_orders_submitted":submitted,"actual_live_orders_submitted":0,"daily_submission_counter":c,
      "next_phase":"V371_01_TO_V380_64_PAPER_EXECUTION_LIFECYCLE_AND_RECONCILIATION"}
    write_json(root/ACTUAL/"latest_controlled_paper_execution_result.json",result);append_jsonl(root/ACTUAL/"controlled_paper_execution_ledger.jsonl",result);return result
