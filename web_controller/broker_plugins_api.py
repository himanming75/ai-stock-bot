from pathlib import Path
from broker_plugins.engine import evaluate
from broker_plugins.dashboard import payload
from broker_plugins.reload import build_plan

def get_payload(root: Path) -> dict:
    return payload(root) or evaluate(root)

def refresh_payload(root: Path) -> dict:
    return {"ok": True, "result": evaluate(root)}

def reload_plan_payload(root: Path, body: dict) -> dict:
    plugin_ids = body.get("plugin_ids", [])
    if not isinstance(plugin_ids, list):
        return {"ok": False, "error": "plugin_ids must be a list"}
    return {"ok": True, "reload_plan": build_plan(root, [str(x) for x in plugin_ids])}
