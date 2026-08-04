from pathlib import Path
from windows_autostart_recovery.dashboard import payload
from windows_autostart_recovery.supervisor import run

def get_payload(root: Path) -> dict:
    return payload(root) or run(root, execute_child=False)

def dry_run_payload(root: Path) -> dict:
    return {"ok": True, "result": run(root, execute_child=False)}
