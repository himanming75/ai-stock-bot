from pathlib import Path
from live_approval.engine import evaluate
from live_approval.dashboard import payload
from live_approval.approval import decide

def get_payload(root:Path)->dict:
    return payload(root) or evaluate(root)

def refresh_payload(root:Path)->dict:
    return {"ok":True,"result":evaluate(root)}

def decision_payload(root:Path,body:dict)->dict:
    return decide(root,str(body.get("decision","")),str(body.get("operator_note","")))
