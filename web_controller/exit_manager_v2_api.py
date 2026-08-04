from pathlib import Path
from exit_manager_v2.dashboard import payload
from exit_manager_v2.engine import evaluate

def get_payload(root: Path) -> dict:
    return payload(root) or evaluate(root)

def refresh_payload(root: Path) -> dict:
    return {"ok": True, "result": evaluate(root)}
