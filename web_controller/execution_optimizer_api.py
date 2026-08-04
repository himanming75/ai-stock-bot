from pathlib import Path
from execution_optimizer.dashboard import payload
from execution_optimizer.engine import evaluate

def get_payload(root: Path) -> dict:
    return payload(root) or evaluate(root)

def refresh_payload(root: Path) -> dict:
    return {"ok": True, "result": evaluate(root)}
