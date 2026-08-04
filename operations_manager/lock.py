from __future__ import annotations
import os
from datetime import datetime,timezone,timedelta
from pathlib import Path
from typing import Any
from operations_manager.io import load_json,write_json

def lock_path(root:Path,name:str)->Path:
    return root/f"release/v156_01_to_v160_64/control/{name}.lock.json"

def acquire(root:Path,name:str,ttl_minutes:int=30)->dict[str,Any]:
    path=lock_path(root,name)
    current=load_json(path)
    now=datetime.now(timezone.utc)
    if current:
        try: created=datetime.fromisoformat(current["created_at"])
        except Exception: created=now-timedelta(days=1)
        if now-created<timedelta(minutes=ttl_minutes):
            return {"acquired":False,"reason":"ACTIVE_LOCK","lock":current}
    value={"name":name,"pid":os.getpid(),"created_at":now.isoformat(),"ttl_minutes":ttl_minutes}
    write_json(path,value)
    return {"acquired":True,"lock":value}

def release(root:Path,name:str)->None:
    path=lock_path(root,name)
    if path.exists(): path.unlink()
