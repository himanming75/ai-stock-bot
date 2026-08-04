from multi_account_engine.dashboard import payload
from multi_account_engine.engine import evaluate
def get_payload(root): return payload(root) or evaluate(root)
def refresh_payload(root): return {"ok":True,"result":evaluate(root)}
