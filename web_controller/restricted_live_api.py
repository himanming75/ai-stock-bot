from pathlib import Path
from restricted_live_automation.engine import evaluate
from restricted_live_automation.dashboard import payload

def get_payload(root:Path)->dict:
    return payload(root) or evaluate(root)

def refresh_payload(root:Path)->dict:
    return {"ok":True,"result":evaluate(root)}
