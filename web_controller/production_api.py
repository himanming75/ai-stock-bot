from pathlib import Path
from production_operations.engine import evaluate
from production_operations.dashboard import payload
from production_operations.backup import create_snapshot,restore_plan

def get_payload(root:Path)->dict:
    return payload(root) or evaluate(root,create_backup=False)

def refresh_payload(root:Path)->dict:
    return {"ok":True,"result":evaluate(root,create_backup=False)}

def backup_payload(root:Path)->dict:
    return {"ok":True,"backup":create_snapshot(root)}

def restore_plan_payload(root:Path)->dict:
    return {"ok":True,"restore_plan":restore_plan(root)}
