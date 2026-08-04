from __future__ import annotations
import shutil
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from production_operations.io import write_json,append_jsonl,sha256_file
from production_operations.config import load

def create_snapshot(root:Path)->dict[str,Any]:
    policy=load(root)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root=root/"release/v186_01_to_v190_64/backups"/stamp
    copied=[];missing=[]
    for rel in policy.get("backup_include_paths",[]):
        src=root/rel
        if not src.exists():
            missing.append(rel);continue
        dst=backup_root/rel
        if src.is_dir():
            shutil.copytree(src,dst,dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    for p in backup_root.rglob("*"):
        if p.is_file():
            copied.append({
                "path":str(p.relative_to(backup_root)).replace("\\","/"),
                "size_bytes":p.stat().st_size,
                "sha256":sha256_file(p),
            })
    manifest={
        "backup_id":stamp,
        "created_at":datetime.now(timezone.utc).isoformat(),
        "backup_root":str(backup_root),
        "file_count":len(copied),
        "files":copied,
        "missing_paths":missing,
        "restore_automatically_allowed":False,
        "broker_credentials_included":False,
        "actual_live_orders_submitted":0,
    }
    write_json(backup_root/"backup_manifest.json",manifest)
    write_json(root/"release/v186_01_to_v190_64/actual/latest_backup.json",manifest)
    append_jsonl(root/"release/v186_01_to_v190_64/actual/backup_ledger.jsonl",{
        "created_at":manifest["created_at"],"backup_id":stamp,
        "file_count":len(copied),"missing_count":len(missing),
        "actual_live_orders_submitted":0,
    })
    prune(root,int(policy.get("maximum_backup_count",30)))
    return manifest

def prune(root:Path,maximum:int)->None:
    folder=root/"release/v186_01_to_v190_64/backups"
    if not folder.exists():return
    rows=sorted([p for p in folder.iterdir() if p.is_dir()],key=lambda p:p.name,reverse=True)
    for old in rows[maximum:]:
        shutil.rmtree(old)

def restore_plan(root:Path)->dict[str,Any]:
    from production_operations.io import load_json
    latest=load_json(root/"release/v186_01_to_v190_64/actual/latest_backup.json")
    result={
        "backup_available":bool(latest),
        "backup_id":latest.get("backup_id"),
        "steps":[
            "STOP_WEB_CONTROLLER",
            "ENABLE_EMERGENCY_STOP",
            "VERIFY_CURRENT_GIT_STATUS",
            "VERIFY_BACKUP_MANIFEST_HASHES",
            "RESTORE_SELECTED_CONFIG_AND_ACTUAL_FILES_MANUALLY",
            "RUN_FULL_TEST_AND_VERIFY",
            "RESTART_PAPER_READ_ONLY_OPERATIONS",
        ],
        "automatic_restore_performed":False,
        "broker_write_enabled":False,
        "actual_live_orders_submitted":0,
    }
    write_json(root/"release/v186_01_to_v190_64/actual/restore_plan.json",result)
    return result
