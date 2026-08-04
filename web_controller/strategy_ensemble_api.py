from pathlib import Path
from ai_strategy_ensemble.engine import evaluate
from ai_strategy_ensemble.dashboard import payload

def get_payload(root:Path)->dict:
    return payload(root) or evaluate(root)

def refresh_payload(root:Path)->dict:
    return {"ok":True,"result":evaluate(root)}
