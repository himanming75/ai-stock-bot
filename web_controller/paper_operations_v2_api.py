from pathlib import Path
from paper_operations_v2.dashboard import payload
from paper_operations_v2.engine import evaluate

def get_payload(root: Path) -> dict:
    return payload(root) or evaluate(root)

def run_cycle_payload(root: Path) -> dict:
    return {"ok": True, "result": evaluate(root)}
