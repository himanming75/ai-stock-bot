from pathlib import Path
from multi_timeframe_strategy.dashboard import payload
from multi_timeframe_strategy.engine import evaluate

def get_payload(root: Path) -> dict:
    return payload(root) or evaluate(root)

def refresh_payload(root: Path) -> dict:
    return {"ok": True, "result": evaluate(root)}
