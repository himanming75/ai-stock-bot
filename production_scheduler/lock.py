from __future__ import annotations
import os
from datetime import datetime,timezone,timedelta
from pathlib import Path
from typing import Any
from production_scheduler.io import load_json,write_json

def path(root:Path,job:str)->Path:
    safe="".join(c for c in job if c.isalnum() or c in ("_","-"))
    return root/f"release/v191_01_to_v195_64/control/{safe}.lock.json"

def acquire(root:Path,job:str,ttl_minutes:int)->dict[str,Any]:
    p=path(root,job)
    current=load_json(p)
    now=datetime.now(timezone.utc)
    if current:
        try: created=datetime.fromisoformat(current["created_at"])
        except Exception: created=now-timedelta(days=1)
        if now-created<timedelta(minutes=ttl_minutes):
            return {"acquired":False,"reason":"ACTIVE_LOCK","lock":current}
    value={"job":job,"pid":os.getpid(),"created_at":now.isoformat(),"ttl_minutes":ttl_minutes}
    write_json(p,value)
    return {"acquired":True,"lock":value}

def release(root:Path,job:str)->None:
    p=path(root,job)
    if p.exists(): p.unlink()
