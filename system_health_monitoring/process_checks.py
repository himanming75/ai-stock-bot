from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def windows_process_snapshot() -> list[dict]:
    if os.name != "nt":
        return []
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -match "
            "'run_paper_automation_controller.py|"
            "automation_watchdog|daily_session_manager' } | "
            "Select-Object ProcessId,ParentProcessId,"
            "Name,CreationDate,CommandLine | "
            "ConvertTo-Json -Depth 3 -Compress"
        ),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    payload = json.loads(completed.stdout)
    if isinstance(payload, dict):
        payload = [payload]
    return payload


def classify_controller_processes(processes: list[dict]) -> dict:
    matching = [
        item
        for item in processes
        if "run_paper_automation_controller.py"
        in str(item.get("CommandLine", ""))
    ]
    ids = {
        int(item.get("ProcessId", 0)): item
        for item in matching
        if item.get("ProcessId")
    }
    roots = []
    children = []
    for item in matching:
        parent = int(item.get("ParentProcessId", 0) or 0)
        if parent in ids:
            children.append(item)
        else:
            roots.append(item)
    return {
        "matching_process_count": len(matching),
        "root_controller_count": len(roots),
        "child_interpreter_count": len(children),
        "duplicate_controller_detected": len(roots) > 1,
        "processes": matching,
    }
