from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RetentionPolicy:
    runtime_log_days: int = 30
    audit_log_days: int = 365
    daily_report_days: int = 365
    backup_count: int = 14
    rotate_max_bytes: int = 25 * 1024 * 1024

    def evaluate(self) -> dict[str, Any]:
        checks = {
            "runtime_log_days_safe": 7 <= self.runtime_log_days <= 90,
            "audit_log_days_safe": 90 <= self.audit_log_days <= 2555,
            "daily_report_days_safe": 90 <= self.daily_report_days <= 2555,
            "backup_count_safe": 7 <= self.backup_count <= 60,
            "rotate_size_safe": (
                1024 * 1024 <= self.rotate_max_bytes <=
                100 * 1024 * 1024
            ),
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "valid": all(checks.values()),
            "policy": {
                "runtime_log_days": self.runtime_log_days,
                "audit_log_days": self.audit_log_days,
                "daily_report_days": self.daily_report_days,
                "backup_count": self.backup_count,
                "rotate_max_bytes": self.rotate_max_bytes,
            },
        }
