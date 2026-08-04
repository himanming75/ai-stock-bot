from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from autonomous_paper_operations.io import copy_if_exists

def create_backup(root: Path, session_date: str) -> dict[str, Any]:
    backup_dir=(
        root/"release/v109_01_to_v110_64/backups"/session_date
    )
    sources=[
        root/"release/v106_33_to_v108_64/actual/fast_track_paper_result.json",
        root/"release/v106_33_to_v108_64/actual/performance_analytics.json",
        root/"release/v106_33_to_v108_64/actual/paper_position_state.json",
        root/"release/v109_01_to_v110_64/actual/autonomous_operations_checkpoint.json",
    ]
    copied=[]
    for source in sources:
        destination=backup_dir/source.name
        if copy_if_exists(source,destination):
            copied.append(destination.name)
    return {
        "created_at":datetime.now(timezone.utc).isoformat(),
        "session_date":session_date,
        "backup_directory":str(backup_dir),
        "copied_files":copied,
        "file_count":len(copied),
        "passed":True,
    }
