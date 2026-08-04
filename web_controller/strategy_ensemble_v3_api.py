from pathlib import Path
from ai_strategy_ensemble_v3.dashboard import payload
from ai_strategy_ensemble_v3.engine import evaluate

def get_payload(root: Path) -> dict:
    return payload(root) or evaluate(root)

def refresh_payload(root: Path) -> dict:
    return {"ok": True, "result": evaluate(root)}
