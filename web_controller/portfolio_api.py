from pathlib import Path
from portfolio_broker.engine import evaluate
from portfolio_broker.dashboard import payload

def get_payload(root:Path)->dict:
    return payload(root) or evaluate(root)

def refresh_payload(root:Path)->dict:
    return {"ok":True,"result":evaluate(root)}
