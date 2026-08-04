from pathlib import Path
from multi_broker_production.engine import evaluate
from multi_broker_production.dashboard import payload

def get_payload(root:Path)->dict:
    return payload(root) or evaluate(root)

def refresh_payload(root:Path)->dict:
    return {"ok":True,"result":evaluate(root)}
