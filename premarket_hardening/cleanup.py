from __future__ import annotations
import gzip
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .runtime_policy import classify_path


def build_cleanup_plan(
    *,
    files: list[dict],
    now: datetime,
    dry_run: bool = True,
) -> dict:
    actions = []
    protected_skipped = 0

    for item in files:
        path = str(item["path"])
        modified = item["modified_at"]
        if isinstance(modified, str):
            modified = datetime.fromisoformat(
                modified.replace("Z", "+00:00")
            )
        age_days = (now - modified).days
        classification = classify_path(path)

        if not classification["runtime"]:
            continue

        lower = path.lower()
        protected = "checkpoint" in lower
        if protected and age_days <= 14:
            protected_skipped += 1
            continue

        if "cycle_" in lower and age_days > 7:
            action = "DELETE"
        elif path.endswith(".jsonl") and age_days > 30:
            action = "COMPRESS"
        elif path.endswith(".log") and age_days > 14:
            action = "COMPRESS"
        else:
            action = "KEEP"

        actions.append({
            "path": path,
            "age_days": age_days,
            "category": classification["category"],
            "action": action,
            "dry_run": dry_run,
        })

    return {
        "actions": actions,
        "protected_skipped": protected_skipped,
        "dry_run": dry_run,
        "delete_count": sum(
            1 for item in actions
            if item["action"] == "DELETE"
        ),
        "compress_count": sum(
            1 for item in actions
            if item["action"] == "COMPRESS"
        ),
    }


def compress_file(path: Path) -> Path:
    destination = path.with_suffix(path.suffix + ".gz")
    with path.open("rb") as source:
        with gzip.open(destination, "wb") as target:
            shutil.copyfileobj(source, target)
    return destination
