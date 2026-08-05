from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SessionPolicy:
    heartbeat_interval_seconds: int = 60
    maximum_heartbeat_age_seconds: int = 180
    require_single_instance: bool = True
    require_profile_snapshot: bool = True
    automatic_order_replay_enabled: bool = False
    automatic_broker_restart_enabled: bool = False

    def validate(self) -> dict[str, Any]:
        checks = {
            "heartbeat_interval_positive": self.heartbeat_interval_seconds > 0,
            "maximum_age_greater_than_interval": (
                self.maximum_heartbeat_age_seconds
                > self.heartbeat_interval_seconds
            ),
            "single_instance_required": self.require_single_instance is True,
            "profile_snapshot_required": self.require_profile_snapshot is True,
            "automatic_order_replay_off": (
                self.automatic_order_replay_enabled is False
            ),
            "automatic_broker_restart_off": (
                self.automatic_broker_restart_enabled is False
            ),
        }
        return {
            "checks": checks,
            "failed": [k for k, v in checks.items() if not v],
            "valid": all(checks.values()),
        }
