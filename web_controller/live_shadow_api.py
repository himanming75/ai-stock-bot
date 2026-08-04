from pathlib import Path
from live_shadow_slippage.dashboard import payload
from live_shadow_slippage.engine import evaluate

def get_payload(root: Path) -> dict:
    return payload(root) or evaluate(root)

def refresh_payload(root: Path) -> dict:
    return {"ok": True, "result": evaluate(root)}
