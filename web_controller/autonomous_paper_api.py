from pathlib import Path
from autonomous_paper_trading.dashboard import payload
from autonomous_paper_trading.engine import evaluate

def get_payload(root: Path) -> dict:
    return payload(root) or evaluate(root, allow_network=False)

def dry_run_payload(root: Path) -> dict:
    return {"ok": True, "result": evaluate(root, allow_network=False)}
