import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from backtest.paper_trading_schedule_planner import (
    PaperTradingSchedulePlan,
)
from backtest.paper_trading_session_summary import (
    PaperTradingSessionSummaryResult,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

SCHEDULED_PAPER_RUN_APPROVAL_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "scheduled_paper_run_approval"
)


VALID_APPROVAL_STATUSES = {
    "APPROVED",
    "REJECTED",
    "BLOCKED",
    "FAILED",
}


VALID_APPROVAL_DECISIONS = {
    "APPROVE",
    "REJECT",
}


@dataclass(frozen=True)
class ScheduledPaperRunApprovalPolicy:
    """
    V11.0 Scheduled Paper Run Approval 정책입니다.

    계획된 Paper Run을 사용자가 실행 직전에 수동 승인합니다.
    """

    required_approval_text: str = (
        "APPROVE PAPER RUN"
    )
    minimum_approval_note_length: int = 5

    maximum_approval_lead_minutes: int = 30
    late_approval_grace_minutes: int = 5
    approval_valid_minutes: int = 15

    require_ready_session: bool = True
    allow_warning_session: bool = False
    allow_review_required_plan: bool = False

    reject_duplicate_plan_approval: bool = True
    retain_rejected_approvals: bool = True
    retain_blocked_approvals: bool = True

    maximum_record_count: int = 1_000
    trim_oldest_records: bool = True

    manual_approval_required: bool = True
    automatic_approval_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScheduledPaperRunApprovalRecord:
    """
    한 Plan에 대한 수동 승인 또는 거부 기록입니다.
    """

    approval_id: str
    created_at: str

    plan_id: str
    schedule_key: str
    scheduled_at: str

    approval_status: str
    approval_status_label: str
    approval_decision: str

    approval_actor: str
    approval_note: str
    approval_text: str

    reviewed_at: str
    approval_expires_at: str | None

    source_summary_id: str
    source_session_status: str
    source_session_action: str

    normalized_symbols: tuple[
        str,
        ...,
    ]
    symbol_count: int

    plan_checks_passed: bool
    timing_checks_passed: bool
    session_checks_passed: bool
    approval_text_checks_passed: bool
    duplicate_checks_passed: bool
    all_checks_passed: bool

    paper_run_authorized: bool
    paper_execution_prepared: bool
    automatic_execution_authorized: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    reasons: tuple[str, ...] = field(
        default_factory=tuple
    )
    warnings: tuple[str, ...] = field(
        default_factory=tuple
    )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["normalized_symbols"] = list(
            self.normalized_symbols
        )
        payload["reasons"] = list(self.reasons)
        payload["warnings"] = list(
            self.warnings
        )
        return payload


@dataclass(frozen=True)
class ScheduledPaperRunApprovalState:
    """
    누적 Approval Record 상태입니다.
    """

    approval_state_id: str
    created_at: str
    updated_at: str

    record_count: int
    approved_count: int
    rejected_count: int
    blocked_count: int
    failed_count: int

    records: tuple[
        ScheduledPaperRunApprovalRecord,
        ...,
    ] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["records"] = [
            record.to_dict()
            for record in self.records
        ]
        return payload


@dataclass
class ScheduledPaperRunApprovalResult:
    """
    V11.0 수동 승인 처리 결과입니다.
    """

    version: str
    created_at: str

    approval_result_id: str
    approval_state_id: str

    approval_status: str
    approval_status_label: str

    plan_id: str | None
    approval_id: str | None

    approval_record_added: bool
    duplicate_detected: bool
    state_trimmed: bool
    trimmed_record_count: int

    previous_record_count: int
    current_record_count: int

    policy_checks_passed: bool
    input_checks_passed: bool
    plan_checks_passed: bool
    timing_checks_passed: bool
    session_checks_passed: bool
    approval_text_checks_passed: bool
    duplicate_checks_passed: bool
    state_checks_passed: bool
    all_checks_passed: bool

    paper_run_authorized: bool
    paper_execution_prepared: bool
    automatic_execution_authorized: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    approval_policy: (
        ScheduledPaperRunApprovalPolicy
    )
    approval_record: (
        ScheduledPaperRunApprovalRecord
        | None
    )
    approval_state: (
        ScheduledPaperRunApprovalState
    )

    reasons: list[str] = field(
        default_factory=list
    )
    warnings: list[str] = field(
        default_factory=list
    )
    next_actions: list[str] = field(
        default_factory=list
    )

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["approval_policy"] = (
            self.approval_policy.to_dict()
        )
        payload["approval_record"] = (
            self.approval_record.to_dict()
            if self.approval_record is not None
            else None
        )
        payload["approval_state"] = (
            self.approval_state.to_dict()
        )
        return payload


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    with temporary_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    temporary_path.replace(file_path)


def read_json_file(
    file_path: Path,
) -> dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON 파일이 없습니다: {file_path}"
        )

    if file_path.stat().st_size <= 0:
        raise RuntimeError(
            f"JSON 파일이 비어 있습니다: {file_path}"
        )

    with file_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise RuntimeError(
            "JSON 최상위 데이터가 Dictionary가 아닙니다."
        )

    return payload


def parse_datetime(
    value: str | datetime,
    field_label: str,
) -> datetime:
    if isinstance(value, datetime):
        return value

    if not isinstance(value, str):
        raise TypeError(
            f"{field_label}은 ISO 문자열 또는 datetime이어야 합니다."
        )

    try:
        return datetime.fromisoformat(
            value.strip()
        )
    except ValueError as error:
        raise ValueError(
            f"{field_label} 형식이 올바르지 않습니다: {value}"
        ) from error


def normalize_decision(
    decision: str,
) -> str:
    if not isinstance(decision, str):
        raise TypeError(
            "Approval Decision은 문자열이어야 합니다."
        )

    normalized = decision.strip().upper()

    if normalized not in VALID_APPROVAL_DECISIONS:
        raise ValueError(
            (
                "Approval Decision은 APPROVE 또는 "
                "REJECT여야 합니다."
            )
        )

    return normalized


def validate_approval_policy(
    policy: ScheduledPaperRunApprovalPolicy,
) -> tuple[bool, list[str]]:
    """
    V11.0 Approval Policy를 검사합니다.
    """

    if not isinstance(
        policy,
        ScheduledPaperRunApprovalPolicy,
    ):
        return (
            False,
            [
                (
                    "Policy가 "
                    "ScheduledPaperRunApprovalPolicy "
                    "형식이 아닙니다."
                )
            ],
        )

    errors: list[str] = []

    if (
        not isinstance(
            policy.required_approval_text,
            str,
        )
        or not policy.required_approval_text.strip()
    ):
        errors.append(
            "Required Approval Text가 비어 있습니다."
        )

    positive_integer_fields = {
        "minimum_approval_note_length": (
            policy.minimum_approval_note_length
        ),
        "maximum_approval_lead_minutes": (
            policy.maximum_approval_lead_minutes
        ),
        "late_approval_grace_minutes": (
            policy.late_approval_grace_minutes
        ),
        "approval_valid_minutes": (
            policy.approval_valid_minutes
        ),
        "maximum_record_count": (
            policy.maximum_record_count
        ),
    }

    for field_name, value in (
        positive_integer_fields.items()
    ):
        if (
            not isinstance(value, int)
            or value <= 0
        ):
            errors.append(
                f"{field_name}는 0보다 큰 int여야 합니다."
            )

    boolean_fields = {
        "require_ready_session": (
            policy.require_ready_session
        ),
        "allow_warning_session": (
            policy.allow_warning_session
        ),
        "allow_review_required_plan": (
            policy.allow_review_required_plan
        ),
        "reject_duplicate_plan_approval": (
            policy.reject_duplicate_plan_approval
        ),
        "retain_rejected_approvals": (
            policy.retain_rejected_approvals
        ),
        "retain_blocked_approvals": (
            policy.retain_blocked_approvals
        ),
        "trim_oldest_records": (
            policy.trim_oldest_records
        ),
        "manual_approval_required": (
            policy.manual_approval_required
        ),
        "automatic_approval_disabled": (
            policy.automatic_approval_disabled
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }

    for field_name, value in boolean_fields.items():
        if not isinstance(value, bool):
            errors.append(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    if not policy.reject_duplicate_plan_approval:
        errors.append(
            "V11.0에서는 Duplicate Plan Approval 차단이 필수입니다."
        )

    if not policy.retain_rejected_approvals:
        errors.append(
            "거부 기록은 Audit 목적으로 보존해야 합니다."
        )

    if not policy.retain_blocked_approvals:
        errors.append(
            "차단 기록은 Audit 목적으로 보존해야 합니다."
        )

    if not policy.manual_approval_required:
        errors.append(
            "V11.0에서는 Manual Approval이 필수입니다."
        )

    if not policy.automatic_approval_disabled:
        errors.append(
            "V11.0에서는 Automatic Approval이 차단되어야 합니다."
        )

    if not policy.paper_only:
        errors.append(
            "V11.0에서는 Paper Only가 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V11.0에서는 Live Execution Disabled가 "
            "True여야 합니다."
        )

    return (not errors, errors)


def validate_schedule_plan(
    plan: PaperTradingSchedulePlan,
    policy: ScheduledPaperRunApprovalPolicy,
) -> tuple[bool, list[str]]:
    """
    V10.9 Plan이 승인 가능한 상태인지 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        plan,
        PaperTradingSchedulePlan,
    ):
        return (
            False,
            [
                (
                    "Plan이 PaperTradingSchedulePlan "
                    "형식이 아닙니다."
                )
            ],
        )

    if not plan.plan_id:
        errors.append(
            "Plan ID가 비어 있습니다."
        )

    if not plan.schedule_key:
        errors.append(
            "Schedule Key가 비어 있습니다."
        )

    allowed_plan = (
        plan.plan_status == "PLANNED"
        and plan.plan_action == "QUEUE"
    )

    allowed_review_plan = (
        policy.allow_review_required_plan
        and plan.plan_status
        == "REVIEW_REQUIRED"
        and plan.plan_action == "REVIEW"
    )

    if not (
        allowed_plan
        or allowed_review_plan
    ):
        errors.append(
            (
                "승인할 수 없는 Plan 상태입니다: "
                f"{plan.plan_status}/{plan.plan_action}"
            )
        )

    if not plan.all_checks_passed:
        errors.append(
            "Plan All Checks가 실패했습니다."
        )

    if not plan.manual_launch_required:
        errors.append(
            "Plan이 Manual Launch를 요구하지 않습니다."
        )

    if plan.automatic_execution_authorized:
        errors.append(
            "Plan의 Automatic Execution이 허용되어 있습니다."
        )

    if not plan.execution_blocked:
        errors.append(
            "Plan Execution이 차단되지 않았습니다."
        )

    if any(
        (
            plan.broker_api_called,
            plan.broker_order_created,
            plan.live_order_created,
            plan.live_execution_authorized,
        )
    ):
        errors.append(
            "Plan의 실거래 안전 상태가 올바르지 않습니다."
        )

    if not plan.normalized_symbols:
        errors.append(
            "Plan의 Symbol 목록이 비어 있습니다."
        )

    if (
        plan.unique_symbol_count
        != len(plan.normalized_symbols)
    ):
        errors.append(
            "Plan의 Unique Symbol Count가 목록과 다릅니다."
        )

    try:
        parse_datetime(
            plan.scheduled_at,
            "Plan Scheduled At",
        )
    except (TypeError, ValueError) as error:
        errors.append(str(error))

    return (not errors, errors)


def validate_current_session(
    summary: PaperTradingSessionSummaryResult,
    policy: ScheduledPaperRunApprovalPolicy,
) -> tuple[bool, bool, list[str]]:
    """
    승인 시점의 최신 V10.8 Session 상태를 검사합니다.
    """

    errors: list[str] = []
    warning_allowed = False

    if not isinstance(
        summary,
        PaperTradingSessionSummaryResult,
    ):
        return (
            False,
            False,
            [
                (
                    "Current Session Summary가 "
                    "V10.8 Result 형식이 아닙니다."
                )
            ],
        )

    if summary.version != "V10.8":
        errors.append(
            "Current Session Summary 버전이 V10.8이 아닙니다."
        )

    if not summary.all_checks_passed:
        errors.append(
            "Current Session Summary All Checks가 실패했습니다."
        )

    if summary.execution_blocked is not True:
        errors.append(
            "Current Session Summary Execution이 차단되지 않았습니다."
        )

    if any(
        (
            summary.broker_api_called,
            summary.broker_order_created,
            summary.live_order_created,
            summary.live_execution_authorized,
        )
    ):
        errors.append(
            "Current Session Summary의 안전 상태가 올바르지 않습니다."
        )

    if summary.session_status == "READY":
        pass
    elif (
        summary.session_status == "WARNING"
        and policy.allow_warning_session
    ):
        warning_allowed = True
    else:
        errors.append(
            (
                "현재 Session 상태에서는 승인할 수 없습니다: "
                f"{summary.session_status}"
            )
        )

    if (
        policy.require_ready_session
        and summary.session_status != "READY"
        and not warning_allowed
    ):
        errors.append(
            "Policy가 READY Session을 요구합니다."
        )

    return (
        not errors,
        warning_allowed,
        errors,
    )


def validate_approval_timing(
    plan: PaperTradingSchedulePlan,
    reviewed_at: datetime,
    policy: ScheduledPaperRunApprovalPolicy,
) -> tuple[
    bool,
    float,
    datetime | None,
    list[str],
]:
    """
    승인 시각이 예정시간 근처인지 검사합니다.

    Minutes Until Run:
    - 양수: 실행 전
    - 음수: 실행 예정시간 경과
    """

    errors: list[str] = []

    try:
        scheduled_at = parse_datetime(
            plan.scheduled_at,
            "Plan Scheduled At",
        )
    except (TypeError, ValueError) as error:
        return (
            False,
            0.0,
            None,
            [str(error)],
        )

    if (
        scheduled_at.tzinfo is not None
        and reviewed_at.tzinfo is None
    ) or (
        scheduled_at.tzinfo is None
        and reviewed_at.tzinfo is not None
    ):
        errors.append(
            "Scheduled At과 Reviewed At의 Timezone 형식이 다릅니다."
        )
        return (
            False,
            0.0,
            None,
            errors,
        )

    minutes_until_run = (
        scheduled_at - reviewed_at
    ).total_seconds() / 60.0

    if (
        minutes_until_run
        > policy.maximum_approval_lead_minutes
    ):
        errors.append(
            (
                "승인 시각이 실행 예정시간보다 너무 빠릅니다. "
                f"최대 {policy.maximum_approval_lead_minutes}분 전까지 허용합니다."
            )
        )

    if (
        minutes_until_run
        < -policy.late_approval_grace_minutes
    ):
        errors.append(
            (
                "실행 예정시간의 승인 유예시간을 초과했습니다. "
                f"최대 {policy.late_approval_grace_minutes}분까지 허용합니다."
            )
        )

    approval_expires_at = reviewed_at + timedelta(
        minutes=policy.approval_valid_minutes
    )

    if approval_expires_at < scheduled_at:
        errors.append(
            (
                "Approval 유효기간이 Scheduled At 전에 만료됩니다."
            )
        )

    return (
        not errors,
        round(minutes_until_run, 4),
        approval_expires_at,
        errors,
    )


def validate_approval_text_input(
    decision: str,
    actor: str,
    note: str,
    approval_text: str,
    policy: ScheduledPaperRunApprovalPolicy,
) -> tuple[bool, list[str]]:
    """
    수동 승인자의 입력을 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(actor, str) or not actor.strip():
        errors.append(
            "Approval Actor가 비어 있습니다."
        )

    if (
        not isinstance(note, str)
        or len(note.strip())
        < policy.minimum_approval_note_length
    ):
        errors.append(
            (
                "Approval Note가 너무 짧습니다. "
                f"최소 {policy.minimum_approval_note_length}자입니다."
            )
        )

    if not isinstance(approval_text, str):
        errors.append(
            "Approval Text는 문자열이어야 합니다."
        )
    elif (
        decision == "APPROVE"
        and approval_text.strip().upper()
        != policy.required_approval_text.upper()
    ):
        errors.append(
            (
                "Required Approval Text가 일치하지 않습니다. "
                f"필요 문구: {policy.required_approval_text}"
            )
        )

    return (not errors, errors)


def empty_approval_state() -> (
    ScheduledPaperRunApprovalState
):
    now = datetime.now().isoformat()

    return ScheduledPaperRunApprovalState(
        approval_state_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        record_count=0,
        approved_count=0,
        rejected_count=0,
        blocked_count=0,
        failed_count=0,
        records=(),
    )


def build_approval_state(
    records: tuple[
        ScheduledPaperRunApprovalRecord,
        ...,
    ],
    approval_state_id: str | None = None,
    created_at: str | None = None,
) -> ScheduledPaperRunApprovalState:
    return ScheduledPaperRunApprovalState(
        approval_state_id=(
            approval_state_id
            or str(uuid.uuid4())
        ),
        created_at=(
            created_at
            or datetime.now().isoformat()
        ),
        updated_at=datetime.now().isoformat(),
        record_count=len(records),
        approved_count=sum(
            record.approval_status == "APPROVED"
            for record in records
        ),
        rejected_count=sum(
            record.approval_status == "REJECTED"
            for record in records
        ),
        blocked_count=sum(
            record.approval_status == "BLOCKED"
            for record in records
        ),
        failed_count=sum(
            record.approval_status == "FAILED"
            for record in records
        ),
        records=records,
    )


def validate_approval_state(
    state: ScheduledPaperRunApprovalState,
) -> tuple[bool, list[str]]:
    """
    Approval State 집계와 중복 Plan ID를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        state,
        ScheduledPaperRunApprovalState,
    ):
        return (
            False,
            [
                (
                    "Approval State가 "
                    "ScheduledPaperRunApprovalState "
                    "형식이 아닙니다."
                )
            ],
        )

    rebuilt = build_approval_state(
        records=state.records,
        approval_state_id=(
            state.approval_state_id
        ),
        created_at=state.created_at,
    )

    count_fields = (
        "record_count",
        "approved_count",
        "rejected_count",
        "blocked_count",
        "failed_count",
    )

    for field_name in count_fields:
        if (
            getattr(state, field_name)
            != getattr(rebuilt, field_name)
        ):
            errors.append(
                f"Approval 집계값 {field_name}가 Record 목록과 다릅니다."
            )

    plan_ids = [
        record.plan_id
        for record in state.records
    ]

    if len(plan_ids) != len(set(plan_ids)):
        errors.append(
            "Approval State에 중복 Plan ID가 있습니다."
        )

    for record in state.records:
        if (
            record.approval_status
            not in VALID_APPROVAL_STATUSES
        ):
            errors.append(
                (
                    "허용되지 않은 Approval Status입니다: "
                    f"{record.approval_status}"
                )
            )

        if record.approval_decision not in (
            VALID_APPROVAL_DECISIONS
        ):
            errors.append(
                (
                    "허용되지 않은 Approval Decision입니다: "
                    f"{record.approval_decision}"
                )
            )

        if record.automatic_execution_authorized:
            errors.append(
                f"{record.approval_id}: Automatic Execution이 허용되었습니다."
            )

        if not record.execution_blocked:
            errors.append(
                f"{record.approval_id}: Execution이 차단되지 않았습니다."
            )

        if any(
            (
                record.broker_api_called,
                record.broker_order_created,
                record.live_order_created,
                record.live_execution_authorized,
            )
        ):
            errors.append(
                f"{record.approval_id}: 실거래 안전 상태가 올바르지 않습니다."
            )

    return (not errors, errors)


def approval_record_from_dict(
    payload: dict[str, Any],
) -> ScheduledPaperRunApprovalRecord:
    values = dict(payload)
    values["normalized_symbols"] = tuple(
        values.get(
            "normalized_symbols",
            [],
        )
    )
    values["reasons"] = tuple(
        values.get("reasons", [])
    )
    values["warnings"] = tuple(
        values.get("warnings", [])
    )

    return ScheduledPaperRunApprovalRecord(
        **values
    )


def approval_state_from_dict(
    payload: dict[str, Any],
) -> ScheduledPaperRunApprovalState:
    if not isinstance(payload, dict):
        raise TypeError(
            "Approval State Payload는 Dictionary여야 합니다."
        )

    records_payload = payload.get(
        "records",
        [],
    )

    if not isinstance(records_payload, list):
        raise ValueError(
            "Approval Records가 List가 아닙니다."
        )

    records = tuple(
        approval_record_from_dict(record)
        for record in records_payload
    )

    return build_approval_state(
        records=records,
        approval_state_id=str(
            payload.get(
                "approval_state_id",
                "",
            )
            or uuid.uuid4()
        ),
        created_at=str(
            payload.get(
                "created_at",
                datetime.now().isoformat(),
            )
        ),
    )


def load_latest_approval_state(
    default_state: (
        ScheduledPaperRunApprovalState
        | None
    ) = None,
) -> ScheduledPaperRunApprovalState:
    latest_path = (
        SCHEDULED_PAPER_RUN_APPROVAL_OUTPUT_DIRECTORY
        / "scheduled_paper_run_approval_latest.json"
    )

    if not latest_path.exists():
        return (
            default_state
            if default_state is not None
            else empty_approval_state()
        )

    payload = read_json_file(
        latest_path
    )

    state_payload = payload.get(
        "approval_state",
        payload,
    )

    return approval_state_from_dict(
        state_payload
    )


def run_scheduled_paper_run_approval(
    schedule_plan: PaperTradingSchedulePlan,
    current_session_summary: (
        PaperTradingSessionSummaryResult
    ),
    approval_decision: str,
    approval_actor: str,
    approval_note: str,
    approval_text: str,
    reviewed_at: str | datetime,
    approval_state: (
        ScheduledPaperRunApprovalState
        | None
    ) = None,
    approval_policy: (
        ScheduledPaperRunApprovalPolicy
        | None
    ) = None,
) -> ScheduledPaperRunApprovalResult:
    """
    V10.9 Plan을 수동 승인하거나 거부합니다.

    승인 결과는 Paper 실행 준비 상태일 뿐,
    Pipeline 또는 Broker 주문을 실행하지 않습니다.
    """

    policy = (
        approval_policy
        if approval_policy is not None
        else ScheduledPaperRunApprovalPolicy()
    )

    policy_valid, policy_errors = (
        validate_approval_policy(
            policy
        )
    )

    input_errors: list[str] = []

    try:
        decision = normalize_decision(
            approval_decision
        )
    except Exception as error:
        decision = "REJECT"
        input_errors.append(str(error))

    try:
        parsed_reviewed_at = (
            parse_datetime(
                reviewed_at,
                "Reviewed At",
            )
        )
    except Exception as error:
        parsed_reviewed_at = None
        input_errors.append(str(error))

    plan_valid, plan_errors = (
        validate_schedule_plan(
            schedule_plan,
            policy,
        )
    )

    (
        session_valid,
        session_warning_allowed,
        session_errors,
    ) = validate_current_session(
        current_session_summary,
        policy,
    )

    approval_text_valid, text_errors = (
        validate_approval_text_input(
            decision=decision,
            actor=approval_actor,
            note=approval_note,
            approval_text=approval_text,
            policy=policy,
        )
    )

    timing_valid = False
    minutes_until_run = 0.0
    approval_expires_at: (
        datetime
        | None
    ) = None
    timing_errors: list[str] = []

    if (
        parsed_reviewed_at is not None
        and isinstance(
            schedule_plan,
            PaperTradingSchedulePlan,
        )
    ):
        (
            timing_valid,
            minutes_until_run,
            approval_expires_at,
            timing_errors,
        ) = validate_approval_timing(
            plan=schedule_plan,
            reviewed_at=(
                parsed_reviewed_at
            ),
            policy=policy,
        )

    working_state = (
        approval_state
        if approval_state is not None
        else load_latest_approval_state()
    )

    state_valid, state_errors = (
        validate_approval_state(
            working_state
        )
    )

    existing_plan_ids = {
        record.plan_id
        for record in working_state.records
    }

    duplicate_detected = bool(
        isinstance(
            schedule_plan,
            PaperTradingSchedulePlan,
        )
        and schedule_plan.plan_id
        in existing_plan_ids
    )
    duplicate_checks_passed = (
        not duplicate_detected
    )

    input_checks_passed = bool(
        not input_errors
        and parsed_reviewed_at is not None
    )

    reasons: list[str] = []
    warnings: list[str] = []
    warnings.extend(policy_errors)
    warnings.extend(input_errors)
    warnings.extend(plan_errors)
    warnings.extend(session_errors)
    warnings.extend(text_errors)
    warnings.extend(timing_errors)
    warnings.extend(state_errors)

    if duplicate_detected:
        warnings.append(
            "해당 Plan ID의 Approval Record가 이미 있습니다."
        )

    approval_record: (
        ScheduledPaperRunApprovalRecord
        | None
    ) = None

    if not policy_valid or not state_valid:
        approval_status = "FAILED"
        approval_status_label = (
            "Approval Policy 또는 State 검사 실패"
        )
    elif not input_checks_passed:
        approval_status = "FAILED"
        approval_status_label = (
            "Approval 입력 검사 실패"
        )
    elif duplicate_detected:
        approval_status = "BLOCKED"
        approval_status_label = (
            "중복 Plan Approval 차단"
        )
    elif decision == "REJECT":
        approval_status = "REJECTED"
        approval_status_label = (
            "사용자가 Paper Run을 거부함"
        )
    elif not plan_valid:
        approval_status = "BLOCKED"
        approval_status_label = (
            "Plan 안전 검사로 승인 차단"
        )
    elif not timing_valid:
        approval_status = "BLOCKED"
        approval_status_label = (
            "승인 시각 검사로 승인 차단"
        )
    elif not session_valid:
        approval_status = "BLOCKED"
        approval_status_label = (
            "현재 Session 상태로 승인 차단"
        )
    elif not approval_text_valid:
        approval_status = "BLOCKED"
        approval_status_label = (
            "수동 승인 입력 검사로 승인 차단"
        )
    else:
        approval_status = "APPROVED"
        approval_status_label = (
            "Scheduled Paper Run 수동 승인 완료"
        )

    paper_run_authorized = (
        approval_status == "APPROVED"
    )
    paper_execution_prepared = (
        approval_status == "APPROVED"
    )

    record_should_be_added = bool(
        not duplicate_detected
        and isinstance(
            schedule_plan,
            PaperTradingSchedulePlan,
        )
        and parsed_reviewed_at is not None
        and (
            approval_status == "APPROVED"
            or (
                approval_status == "REJECTED"
                and policy.retain_rejected_approvals
            )
            or (
                approval_status == "BLOCKED"
                and policy.retain_blocked_approvals
            )
        )
    )

    if record_should_be_added:
        if approval_status == "APPROVED":
            record_reasons = [
                (
                    f"{approval_actor.strip()} 사용자가 "
                    "Scheduled Paper Run을 승인했습니다."
                ),
                (
                    f"실행 예정시간까지 "
                    f"{minutes_until_run:.4f}분 남았습니다."
                ),
            ]
        elif approval_status == "REJECTED":
            record_reasons = [
                (
                    f"{approval_actor.strip()} 사용자가 "
                    "Scheduled Paper Run을 거부했습니다."
                )
            ]
        else:
            record_reasons = [
                "안전 검사 실패로 Scheduled Paper Run 승인이 차단되었습니다."
            ]

        record_warnings = list(warnings)
        record_warnings.extend(
            [
                (
                    "V11.0 Approval은 Paper 실행 준비만 허용합니다."
                ),
                (
                    "실제 Broker API와 Live Execution은 차단됩니다."
                ),
            ]
        )

        approval_record = (
            ScheduledPaperRunApprovalRecord(
                approval_id=str(uuid.uuid4()),
                created_at=(
                    datetime.now().isoformat()
                ),
                plan_id=schedule_plan.plan_id,
                schedule_key=(
                    schedule_plan.schedule_key
                ),
                scheduled_at=(
                    schedule_plan.scheduled_at
                ),
                approval_status=(
                    approval_status
                ),
                approval_status_label=(
                    approval_status_label
                ),
                approval_decision=decision,
                approval_actor=(
                    approval_actor.strip()
                ),
                approval_note=(
                    approval_note.strip()
                ),
                approval_text=(
                    approval_text.strip()
                ),
                reviewed_at=(
                    parsed_reviewed_at
                    .isoformat(
                        timespec="seconds"
                    )
                ),
                approval_expires_at=(
                    approval_expires_at
                    .isoformat(
                        timespec="seconds"
                    )
                    if (
                        approval_status
                        == "APPROVED"
                        and approval_expires_at
                        is not None
                    )
                    else None
                ),
                source_summary_id=(
                    current_session_summary
                    .session_summary_id
                ),
                source_session_status=(
                    current_session_summary
                    .session_status
                ),
                source_session_action=(
                    current_session_summary
                    .session_action
                ),
                normalized_symbols=tuple(
                    schedule_plan
                    .normalized_symbols
                ),
                symbol_count=len(
                    schedule_plan
                    .normalized_symbols
                ),
                plan_checks_passed=(
                    plan_valid
                ),
                timing_checks_passed=(
                    timing_valid
                ),
                session_checks_passed=(
                    session_valid
                ),
                approval_text_checks_passed=(
                    approval_text_valid
                ),
                duplicate_checks_passed=(
                    duplicate_checks_passed
                ),
                all_checks_passed=(
                    approval_status
                    in {
                        "APPROVED",
                        "REJECTED",
                        "BLOCKED",
                    }
                ),
                paper_run_authorized=(
                    paper_run_authorized
                ),
                paper_execution_prepared=(
                    paper_execution_prepared
                ),
                automatic_execution_authorized=False,
                execution_blocked=True,
                broker_api_called=False,
                broker_order_created=False,
                live_order_created=False,
                live_execution_authorized=False,
                reasons=tuple(
                    record_reasons
                ),
                warnings=tuple(
                    record_warnings
                ),
            )
        )

    approval_record_added = False
    state_trimmed = False
    trimmed_record_count = 0
    previous_record_count = (
        working_state.record_count
    )

    if approval_record is not None:
        updated_records = (
            *working_state.records,
            approval_record,
        )

        if (
            len(updated_records)
            > policy.maximum_record_count
        ):
            if policy.trim_oldest_records:
                trimmed_record_count = (
                    len(updated_records)
                    - policy.maximum_record_count
                )
                updated_records = (
                    updated_records[
                        trimmed_record_count:
                    ]
                )
                state_trimmed = True
            else:
                warnings.append(
                    "Maximum Record Count를 초과했습니다."
                )
                updated_records = (
                    working_state.records
                )
                approval_record = None

        if approval_record is not None:
            updated_state = (
                build_approval_state(
                    records=tuple(
                        updated_records
                    ),
                    approval_state_id=(
                        working_state
                        .approval_state_id
                    ),
                    created_at=(
                        working_state
                        .created_at
                    ),
                )
            )
            approval_record_added = True
        else:
            updated_state = working_state
    else:
        updated_state = working_state

    updated_state_valid, updated_state_errors = (
        validate_approval_state(
            updated_state
        )
    )
    warnings.extend(
        updated_state_errors
    )

    all_checks_passed = bool(
        policy_valid
        and state_valid
        and updated_state_valid
        and approval_status
        in VALID_APPROVAL_STATUSES
        and (
            approval_record_added
            or duplicate_detected
            or approval_status == "FAILED"
        )
    )

    if approval_status == "APPROVED":
        reasons.append(
            "사용자 수동 승인으로 Paper 실행 준비가 완료되었습니다."
        )
        if session_warning_allowed:
            warnings.append(
                "WARNING Session을 Policy에 따라 조건부 승인했습니다."
            )
        next_actions = [
            "Approval 만료 전 현재 Risk와 Session을 다시 확인합니다.",
            "다음 단계에서 승인된 Paper Run만 수동 실행합니다.",
        ]
    elif approval_status == "REJECTED":
        reasons.append(
            "사용자 결정으로 Scheduled Paper Run을 실행하지 않습니다."
        )
        next_actions = [
            "거부 사유와 Approval Note를 보관합니다.",
            "필요하면 새로운 Schedule Plan을 생성합니다.",
        ]
    elif duplicate_detected:
        reasons.append(
            "동일 Plan ID의 중복 Approval을 차단했습니다."
        )
        next_actions = [
            "기존 Approval Record를 확인합니다.",
            "동일 Plan을 다시 승인하지 않습니다.",
        ]
    else:
        reasons.append(
            "입력, Plan, Timing 또는 Session 검사로 승인을 차단했습니다."
        )
        next_actions = [
            "Warnings와 차단 조건을 확인합니다.",
            "필요하면 새로운 Plan을 생성한 후 다시 승인합니다.",
        ]

    warnings.extend(
        [
            (
                "V11.0은 Scheduled Paper Run의 "
                "수동 승인 기록입니다."
            ),
            (
                "승인은 자동 실행이나 Broker 주문을 의미하지 않습니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 "
                "Live Execution은 모두 차단됩니다."
            ),
        ]
    )

    result = ScheduledPaperRunApprovalResult(
        version="V11.0",
        created_at=datetime.now().isoformat(),
        approval_result_id=str(uuid.uuid4()),
        approval_state_id=(
            updated_state.approval_state_id
        ),
        approval_status=approval_status,
        approval_status_label=(
            approval_status_label
        ),
        plan_id=(
            schedule_plan.plan_id
            if isinstance(
                schedule_plan,
                PaperTradingSchedulePlan,
            )
            else None
        ),
        approval_id=(
            approval_record.approval_id
            if approval_record is not None
            else None
        ),
        approval_record_added=(
            approval_record_added
        ),
        duplicate_detected=(
            duplicate_detected
        ),
        state_trimmed=state_trimmed,
        trimmed_record_count=(
            trimmed_record_count
        ),
        previous_record_count=(
            previous_record_count
        ),
        current_record_count=(
            updated_state.record_count
        ),
        policy_checks_passed=(
            policy_valid
        ),
        input_checks_passed=(
            input_checks_passed
        ),
        plan_checks_passed=plan_valid,
        timing_checks_passed=(
            timing_valid
        ),
        session_checks_passed=(
            session_valid
        ),
        approval_text_checks_passed=(
            approval_text_valid
        ),
        duplicate_checks_passed=(
            duplicate_checks_passed
        ),
        state_checks_passed=(
            updated_state_valid
        ),
        all_checks_passed=(
            all_checks_passed
        ),
        paper_run_authorized=(
            paper_run_authorized
        ),
        paper_execution_prepared=(
            paper_execution_prepared
        ),
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        approval_policy=policy,
        approval_record=approval_record,
        approval_state=updated_state,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_scheduled_paper_run_approval(
        result
    )

    return result


def save_scheduled_paper_run_approval(
    result: ScheduledPaperRunApprovalResult,
) -> tuple[Path, Path]:
    """
    V11.0 Report와 Latest Approval State를 저장합니다.
    """

    SCHEDULED_PAPER_RUN_APPROVAL_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    report_path = (
        SCHEDULED_PAPER_RUN_APPROVAL_OUTPUT_DIRECTORY
        / (
            "scheduled_paper_run_approval_"
            f"{timestamp}.json"
        )
    )
    latest_path = (
        SCHEDULED_PAPER_RUN_APPROVAL_OUTPUT_DIRECTORY
        / (
            "scheduled_paper_run_approval_"
            "latest.json"
        )
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)

    payload = result.to_dict()

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)

    return (report_path, latest_path)


def load_latest_scheduled_paper_run_approval() -> (
    dict[str, Any]
):
    latest_path = (
        SCHEDULED_PAPER_RUN_APPROVAL_OUTPUT_DIRECTORY
        / (
            "scheduled_paper_run_approval_"
            "latest.json"
        )
    )

    return read_json_file(latest_path)


def print_scheduled_paper_run_approval(
    result: ScheduledPaperRunApprovalResult,
) -> None:
    """
    V11.0 Approval 결과를 터미널에 출력합니다.
    """

    line_length = 140

    print()
    print("=" * line_length)
    print(
        "V11.0 SCHEDULED PAPER RUN APPROVAL"
    )
    print("=" * line_length)

    print(
        f"Approval status                : "
        f"{result.approval_status}"
    )
    print(
        f"Approval status label          : "
        f"{result.approval_status_label}"
    )
    print(
        f"Approval result ID             : "
        f"{result.approval_result_id}"
    )
    print(
        f"Approval state ID              : "
        f"{result.approval_state_id}"
    )
    print(
        f"Plan ID                        : "
        f"{result.plan_id}"
    )
    print(
        f"Approval ID                    : "
        f"{result.approval_id}"
    )

    print()
    print("APPROVAL UPDATE")
    print("-" * line_length)

    print(
        f"Record added                   : "
        f"{result.approval_record_added}"
    )
    print(
        f"Duplicate detected             : "
        f"{result.duplicate_detected}"
    )
    print(
        f"Previous record count          : "
        f"{result.previous_record_count}"
    )
    print(
        f"Current record count           : "
        f"{result.current_record_count}"
    )
    print(
        f"Paper run authorized           : "
        f"{result.paper_run_authorized}"
    )
    print(
        f"Paper execution prepared       : "
        f"{result.paper_execution_prepared}"
    )

    if result.approval_record is not None:
        record = result.approval_record

        print()
        print("APPROVAL RECORD")
        print("-" * line_length)

        print(
            f"Decision                       : "
            f"{record.approval_decision}"
        )
        print(
            f"Actor                          : "
            f"{record.approval_actor}"
        )
        print(
            f"Reviewed at                    : "
            f"{record.reviewed_at}"
        )
        print(
            f"Scheduled at                   : "
            f"{record.scheduled_at}"
        )
        print(
            f"Approval expires at            : "
            f"{record.approval_expires_at}"
        )
        print(
            f"Symbols                        : "
            f"{', '.join(record.normalized_symbols)}"
        )

    print()
    print("VALIDATION")
    print("-" * line_length)

    print(
        f"Policy checks passed           : "
        f"{result.policy_checks_passed}"
    )
    print(
        f"Input checks passed            : "
        f"{result.input_checks_passed}"
    )
    print(
        f"Plan checks passed             : "
        f"{result.plan_checks_passed}"
    )
    print(
        f"Timing checks passed           : "
        f"{result.timing_checks_passed}"
    )
    print(
        f"Session checks passed          : "
        f"{result.session_checks_passed}"
    )
    print(
        f"Approval text checks passed    : "
        f"{result.approval_text_checks_passed}"
    )
    print(
        f"Duplicate checks passed        : "
        f"{result.duplicate_checks_passed}"
    )
    print(
        f"State checks passed            : "
        f"{result.state_checks_passed}"
    )
    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * line_length)

    print(
        f"Automatic execution authorized : "
        f"{result.automatic_execution_authorized}"
    )
    print(
        f"Execution blocked              : "
        f"{result.execution_blocked}"
    )
    print(
        f"Broker API called              : "
        f"{result.broker_api_called}"
    )
    print(
        f"Broker order created           : "
        f"{result.broker_order_created}"
    )
    print(
        f"Live order created             : "
        f"{result.live_order_created}"
    )
    print(
        f"Live execution authorized      : "
        f"{result.live_execution_authorized}"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * line_length)

        for reason in result.reasons:
            print(f"- {reason}")

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * line_length)

        for warning in result.warnings:
            print(f"- {warning}")

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * line_length)

        for action in result.next_actions:
            print(f"- {action}")

    print()
    print("FILES")
    print("-" * line_length)

    print(
        f"Report file                    : "
        f"{result.report_path or 'Not saved yet'}"
    )
    print(
        f"Latest file                    : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * line_length)
    print(
        "주의: V11.0은 Paper Run 승인만 기록하며 "
        "실제 또는 자동 주문을 수행하지 않습니다."
    )
