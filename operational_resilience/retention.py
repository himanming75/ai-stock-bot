from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any


class DataRetentionPlanner:
    def plan(
        self,
        *,
        records: list[dict[str, Any]],
        retain_days: int,
        observed_at: datetime,
    ) -> dict[str, Any]:
        if retain_days <= 0:
            raise ValueError("POSITIVE_RETENTION_REQUIRED")

        cutoff = observed_at - timedelta(days=retain_days)
        keep = []
        archive = []

        for record in records:
            timestamp = datetime.fromisoformat(
                str(record["created_at"]).replace("Z", "+00:00")
            )
            target = keep if timestamp >= cutoff else archive
            target.append(record)

        return {
            "retain_days": retain_days,
            "cutoff": cutoff.isoformat(),
            "keep_count": len(keep),
            "archive_count": len(archive),
            "keep": keep,
            "archive": archive,
            "actual_files_deleted": False,
            "actual_files_archived": False,
        }
