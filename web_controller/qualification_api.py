from pathlib import Path
from paper_qualification.engine import evaluate
from paper_qualification.dashboard import payload

def get_payload(root:Path)->dict:
    value=payload(root)
    return value or evaluate(root)

def run_payload(root:Path)->dict:
    return {"ok":True,"result":evaluate(root)}
