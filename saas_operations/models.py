from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ServiceStatus:
    service_name: str
    status: str
    heartbeat_age_seconds: float
    restart_count: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Notification:
    notification_id: str
    channel: str
    severity: str
    subject: str
    body: str
    status: str
    attempts: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
