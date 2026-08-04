from __future__ import annotations
import subprocess
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from operations_manager.config import load
from operations_manager.io import append_jsonl

def notify(root:Path,level:str,title:str,message:str)->dict[str,Any]:
    config=load(root)
    row={
        "observed_at":datetime.now(timezone.utc).isoformat(),
        "level":level,"title":title,"message":message,
        "desktop_attempted":False,"desktop_delivered":False,
        "email_attempted":False,"telegram_attempted":False,
    }
    if config.get("desktop_notifications_enabled"):
        row["desktop_attempted"]=True
        safe_title=title.replace("'","''")
        safe_message=message.replace("'","''")
        command=(
            "[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');"
            f"[System.Windows.Forms.MessageBox]::Show('{safe_message}','{safe_title}')"
        )
        try:
            completed=subprocess.run(
                ["powershell","-NoProfile","-Command",command],
                capture_output=True,text=True,timeout=5,
            )
            row["desktop_delivered"]=completed.returncode==0
        except Exception:
            row["desktop_delivered"]=False
    append_jsonl(
        root/"release/v156_01_to_v160_64/actual/notification_ledger.jsonl",
        row,
    )
    return row
