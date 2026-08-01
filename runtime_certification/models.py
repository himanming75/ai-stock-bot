from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class CertificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True)
class CertificationCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class RuntimeCertificate:
    schema_version: int
    certificate_id: str
    generated_at: datetime
    stage_range: str
    release_candidate: str
    certification_status: CertificationStatus
    checks: tuple[CertificationCheck, ...]
    stress_cycles: int
    restart_count: int
    recovery_count: int
    event_count: int
    state_consistent: bool
    event_order_consistent: bool
    recovery_consistent: bool
    portfolio_consistent: bool
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int
    certificate_sha256: str

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["generated_at"] = self.generated_at.isoformat()
        raw["certification_status"] = self.certification_status.value
        raw["checks"] = [asdict(item) for item in self.checks]
        return raw
