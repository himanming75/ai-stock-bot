from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, time, timezone
from typing import Any

from .i18n import bilingual


@dataclass(frozen=True)
class SessionPlan:
    current_state: str
    next_state: str
    planned_action: str
    market_open_required: bool
    execution_enabled: bool
    notes_en: str
    notes_ko: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["next_state_i18n"] = bilingual(
            self.next_state
            if self.next_state
            in {"READY", "BLOCKED"}
            else "READY"
        )
        return value


def build_session_plan(
    *,
    market_status: str,
    configuration_ready: bool,
    broker_read_ready: bool,
    controller_ready: bool,
) -> dict:
    normalized = market_status.upper()

    if not configuration_ready:
        plan = SessionPlan(
            current_state="PREMARKET",
            next_state="BLOCKED",
            planned_action=(
                "WAIT_FOR_CONFIGURATION"
            ),
            market_open_required=False,
            execution_enabled=False,
            notes_en=(
                "Configuration is not ready."
            ),
            notes_ko=(
                "설정이 준비되지 않았습니다."
            ),
        )
    elif not broker_read_ready:
        plan = SessionPlan(
            current_state="PREMARKET",
            next_state="BLOCKED",
            planned_action=(
                "WAIT_FOR_BROKER_READ"
            ),
            market_open_required=False,
            execution_enabled=False,
            notes_en=(
                "Broker read validation is required."
            ),
            notes_ko=(
                "브로커 조회 검증이 필요합니다."
            ),
        )
    elif normalized == "CLOSED":
        plan = SessionPlan(
            current_state="PREMARKET",
            next_state="READY",
            planned_action=(
                "WAIT_FOR_MARKET_OPEN"
            ),
            market_open_required=True,
            execution_enabled=False,
            notes_en=(
                "Premarket checks passed. "
                "Wait for market open validation."
            ),
            notes_ko=(
                "장전 검사가 통과되었습니다. "
                "시장 개장 검증을 기다립니다."
            ),
        )
    elif normalized == "OPEN":
        plan = SessionPlan(
            current_state="MARKET_OPEN",
            next_state="READY",
            planned_action=(
                "PREPARE_INTRADAY_READ_ONLY_VALIDATION"
            ),
            market_open_required=True,
            execution_enabled=False,
            notes_en=(
                "Market is open. Prepare read-only "
                "intraday validation."
            ),
            notes_ko=(
                "시장이 열렸습니다. 조회 전용 장중 "
                "검증을 준비합니다."
            ),
        )
    else:
        plan = SessionPlan(
            current_state="UNKNOWN",
            next_state="BLOCKED",
            planned_action=(
                "REQUIRE_MARKET_STATUS"
            ),
            market_open_required=False,
            execution_enabled=False,
            notes_en=(
                "Market status is unknown."
            ),
            notes_ko=(
                "시장 상태를 확인할 수 없습니다."
            ),
        )

    result = plan.to_dict()
    result.update({
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "controller_ready": (
            controller_ready
        ),
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "order_cancel_enabled": False,
        "automatic_start_enabled": False,
        "automatic_stop_enabled": False,
    })
    return result
