import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from backtest.paper_trading_schedule_planner import (
    PaperTradingSchedulePlan,
)
from backtest.scheduled_paper_run_approval import (
    ScheduledPaperRunApprovalRecord,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

APPROVED_PAPER_RUN_LAUNCHER_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "approved_paper_run_launcher"
)

VALID_LAUNCH_STATUSES = {
    "COMPLETED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class ApprovedPaperRunLauncherPolicy:
    """
    V11.1 Approved Paper Run Launcher 정책입니다.

    V11.0에서 승인된 Paper Run만 사용자가 직접 실행합니다.
    """

    required_launch_text: str = "LAUNCH PAPER RUN"
    minimum_launch_note_length: int = 5
    maximum_late_launch_minutes: int = 5
    maximum_launch_record_count: int = 1_000

    require_approved_record: bool = True
    require_unexpired_approval: bool = True
    require_matching_plan: bool = True
    reject_duplicate_launch: bool = True
    trim_oldest_records: bool = True

    manual_launch_required: bool = True
    automatic_execution_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApprovedPaperRunLaunchRecord:
    launch_id: str
    created_at: str

    approval_id: str
    plan_id: str
    schedule_key: str
    scheduled_at: str

    launch_status: str
    launch_status_label: str
    launch_actor: str
    launch_note: str
    launch_text: str
    launched_at: str

    executor_called: bool
    executor_result_type: str | None
    executor_checks_passed: bool
    paper_run_completed: bool

    approval_checks_passed: bool
    plan_checks_passed: bool
    timing_checks_passed: bool
    input_checks_passed: bool
    duplicate_checks_passed: bool
    all_checks_passed: bool

    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    reasons: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reasons"] = list(self.reasons)
        payload["warnings"] = list(self.warnings)
        return payload


@dataclass(frozen=True)
class ApprovedPaperRunLauncherState:
    launcher_state_id: str
    created_at: str
    updated_at: str

    record_count: int
    completed_count: int
    blocked_count: int
    failed_count: int

    records: tuple[
        ApprovedPaperRunLaunchRecord,
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
class ApprovedPaperRunLauncherResult:
    version: str
    created_at: str

    launcher_result_id: str
    launcher_state_id: str
    launch_id: str | None
    approval_id: str | None
    plan_id: str | None

    launch_status: str
    launch_status_label: str

    executor_called: bool
    executor_result: Any
    paper_run_completed: bool
    duplicate_detected: bool
    record_added: bool
    state_trimmed: bool
    trimmed_record_count: int

    policy_checks_passed: bool
    approval_checks_passed: bool
    plan_checks_passed: bool
    timing_checks_passed: bool
    input_checks_passed: bool
    duplicate_checks_passed: bool
    executor_checks_passed: bool
    state_checks_passed: bool
    all_checks_passed: bool

    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    launcher_policy: ApprovedPaperRunLauncherPolicy
    launch_record: ApprovedPaperRunLaunchRecord | None
    launcher_state: ApprovedPaperRunLauncherState

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["launcher_policy"] = (
            self.launcher_policy.to_dict()
        )
        payload["launch_record"] = (
            self.launch_record.to_dict()
            if self.launch_record is not None
            else None
        )
        payload["launcher_state"] = (
            self.launcher_state.to_dict()
        )

        try:
            json.dumps(payload["executor_result"])
        except (TypeError, ValueError):
            payload["executor_result"] = repr(
                payload["executor_result"]
            )

        return payload


def parse_datetime(
    value: str | datetime,
    field_label: str,
) -> datetime:
    if isinstance(value, datetime):
        return value

    if not isinstance(value, str) or not value.strip():
        raise TypeError(
            f"{field_label}은 datetime 또는 ISO 문자열이어야 합니다."
        )

    try:
        return datetime.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError(
            f"{field_label} 형식이 올바르지 않습니다: {value}"
        ) from error


def write_json_file(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temporary_path.replace(path)


def read_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError(
            "JSON 최상위 값은 object여야 합니다."
        )

    return payload


def validate_launcher_policy(
    policy: ApprovedPaperRunLauncherPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        ApprovedPaperRunLauncherPolicy,
    ):
        return (
            False,
            ["Launcher Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []

    if (
        not isinstance(policy.required_launch_text, str)
        or not policy.required_launch_text.strip()
    ):
        errors.append(
            "Required Launch Text가 비어 있습니다."
        )

    integer_fields = {
        "minimum_launch_note_length": (
            policy.minimum_launch_note_length
        ),
        "maximum_late_launch_minutes": (
            policy.maximum_late_launch_minutes
        ),
        "maximum_launch_record_count": (
            policy.maximum_launch_record_count
        ),
    }
    for name, value in integer_fields.items():
        if (
            not isinstance(value, int)
            or value <= 0
        ):
            errors.append(
                f"{name}는 0보다 큰 int여야 합니다."
            )

    required_true = {
        "require_approved_record": (
            policy.require_approved_record
        ),
        "require_unexpired_approval": (
            policy.require_unexpired_approval
        ),
        "require_matching_plan": (
            policy.require_matching_plan
        ),
        "reject_duplicate_launch": (
            policy.reject_duplicate_launch
        ),
        "manual_launch_required": (
            policy.manual_launch_required
        ),
        "automatic_execution_disabled": (
            policy.automatic_execution_disabled
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }
    for name, value in required_true.items():
        if value is not True:
            errors.append(
                f"{name}는 V11.1에서 True여야 합니다."
            )

    if not isinstance(
        policy.trim_oldest_records,
        bool,
    ):
        errors.append(
            "trim_oldest_records가 bool 형식이 아닙니다."
        )

    return (not errors, errors)


def validate_approval_record(
    approval: ScheduledPaperRunApprovalRecord,
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not isinstance(
        approval,
        ScheduledPaperRunApprovalRecord,
    ):
        return (
            False,
            ["V11.0 Approval Record 형식이 아닙니다."],
        )

    if approval.approval_status != "APPROVED":
        errors.append(
            "Approval Status가 APPROVED가 아닙니다."
        )
    if not approval.all_checks_passed:
        errors.append(
            "Approval All Checks가 실패했습니다."
        )
    if not approval.paper_run_authorized:
        errors.append(
            "Paper Run이 승인되지 않았습니다."
        )
    if not approval.paper_execution_prepared:
        errors.append(
            "Paper Execution이 준비되지 않았습니다."
        )
    if approval.automatic_execution_authorized:
        errors.append(
            "Automatic Execution이 허용되어 있습니다."
        )
    if approval.execution_blocked is not True:
        errors.append(
            "Approval 단계의 Execution 차단 상태가 올바르지 않습니다."
        )
    if any(
        (
            approval.broker_api_called,
            approval.broker_order_created,
            approval.live_order_created,
            approval.live_execution_authorized,
        )
    ):
        errors.append(
            "Approval Record에 실거래 신호가 있습니다."
        )
    if not approval.approval_expires_at:
        errors.append(
            "Approval Expires At이 비어 있습니다."
        )

    return (not errors, errors)


def validate_plan_match(
    plan: PaperTradingSchedulePlan,
    approval: ScheduledPaperRunApprovalRecord,
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not isinstance(plan, PaperTradingSchedulePlan):
        return (
            False,
            ["V10.9 Schedule Plan 형식이 아닙니다."],
        )

    if plan.plan_id != approval.plan_id:
        errors.append(
            "Plan ID가 Approval Record와 다릅니다."
        )
    if plan.schedule_key != approval.schedule_key:
        errors.append(
            "Schedule Key가 Approval Record와 다릅니다."
        )
    if plan.scheduled_at != approval.scheduled_at:
        errors.append(
            "Scheduled At이 Approval Record와 다릅니다."
        )
    if (
        tuple(plan.normalized_symbols)
        != tuple(approval.normalized_symbols)
    ):
        errors.append(
            "Symbol 목록이 Approval Record와 다릅니다."
        )
    if plan.plan_status != "PLANNED":
        errors.append(
            "Plan Status가 PLANNED가 아닙니다."
        )
    if plan.plan_action != "QUEUE":
        errors.append(
            "Plan Action이 QUEUE가 아닙니다."
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
            "Plan의 자동 실행이 허용되어 있습니다."
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
            "Plan에 실거래 신호가 있습니다."
        )

    return (not errors, errors)


def validate_launch_input(
    actor: str,
    note: str,
    launch_text: str,
    policy: ApprovedPaperRunLauncherPolicy,
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if not isinstance(actor, str) or not actor.strip():
        errors.append("Launch Actor가 비어 있습니다.")
    if (
        not isinstance(note, str)
        or len(note.strip())
        < policy.minimum_launch_note_length
    ):
        errors.append(
            "Launch Note가 너무 짧습니다."
        )
    if (
        not isinstance(launch_text, str)
        or launch_text.strip().upper()
        != policy.required_launch_text.upper()
    ):
        errors.append(
            (
                "Required Launch Text가 일치하지 않습니다. "
                f"필요 문구: {policy.required_launch_text}"
            )
        )

    return (not errors, errors)


def validate_launch_timing(
    approval: ScheduledPaperRunApprovalRecord,
    launched_at: datetime,
    policy: ApprovedPaperRunLauncherPolicy,
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    try:
        scheduled_at = parse_datetime(
            approval.scheduled_at,
            "Scheduled At",
        )
        expires_at = parse_datetime(
            approval.approval_expires_at,
            "Approval Expires At",
        )
    except (TypeError, ValueError) as error:
        return (False, [str(error)])

    timezone_values = (
        scheduled_at.tzinfo is not None,
        expires_at.tzinfo is not None,
        launched_at.tzinfo is not None,
    )
    if len(set(timezone_values)) != 1:
        return (
            False,
            ["승인·계획·실행 시각의 Timezone 형식이 다릅니다."],
        )

    if launched_at > expires_at:
        errors.append(
            "Approval 유효시간이 만료되었습니다."
        )

    minutes_late = (
        launched_at - scheduled_at
    ).total_seconds() / 60.0
    if minutes_late > policy.maximum_late_launch_minutes:
        errors.append(
            "Scheduled At 이후 실행 허용시간을 초과했습니다."
        )

    return (not errors, errors)


def empty_launcher_state() -> ApprovedPaperRunLauncherState:
    now = datetime.now().isoformat()
    return ApprovedPaperRunLauncherState(
        launcher_state_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        record_count=0,
        completed_count=0,
        blocked_count=0,
        failed_count=0,
        records=(),
    )


def build_launcher_state(
    records: tuple[
        ApprovedPaperRunLaunchRecord,
        ...,
    ],
    launcher_state_id: str,
    created_at: str,
) -> ApprovedPaperRunLauncherState:
    return ApprovedPaperRunLauncherState(
        launcher_state_id=launcher_state_id,
        created_at=created_at,
        updated_at=datetime.now().isoformat(),
        record_count=len(records),
        completed_count=sum(
            record.launch_status == "COMPLETED"
            for record in records
        ),
        blocked_count=sum(
            record.launch_status == "BLOCKED"
            for record in records
        ),
        failed_count=sum(
            record.launch_status == "FAILED"
            for record in records
        ),
        records=records,
    )


def validate_launcher_state(
    state: ApprovedPaperRunLauncherState,
) -> tuple[bool, list[str]]:
    if not isinstance(
        state,
        ApprovedPaperRunLauncherState,
    ):
        return (
            False,
            ["Launcher State 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    if state.record_count != len(state.records):
        errors.append(
            "Launcher Record Count가 목록과 다릅니다."
        )
    if state.completed_count != sum(
        record.launch_status == "COMPLETED"
        for record in state.records
    ):
        errors.append(
            "Completed Count가 올바르지 않습니다."
        )
    if state.blocked_count != sum(
        record.launch_status == "BLOCKED"
        for record in state.records
    ):
        errors.append(
            "Blocked Count가 올바르지 않습니다."
        )
    if state.failed_count != sum(
        record.launch_status == "FAILED"
        for record in state.records
    ):
        errors.append(
            "Failed Count가 올바르지 않습니다."
        )
    if len(
        {
            record.approval_id
            for record in state.records
        }
    ) != len(state.records):
        errors.append(
            "중복 Approval ID Launch Record가 있습니다."
        )

    return (not errors, errors)


def launch_record_from_dict(
    payload: dict[str, Any],
) -> ApprovedPaperRunLaunchRecord:
    return ApprovedPaperRunLaunchRecord(
        **{
            **payload,
            "reasons": tuple(payload.get("reasons", [])),
            "warnings": tuple(
                payload.get("warnings", [])
            ),
        }
    )


def launcher_state_from_dict(
    payload: dict[str, Any],
) -> ApprovedPaperRunLauncherState:
    records = tuple(
        launch_record_from_dict(item)
        for item in payload.get("records", [])
    )
    return build_launcher_state(
        records=records,
        launcher_state_id=payload[
            "launcher_state_id"
        ],
        created_at=payload["created_at"],
    )


def load_latest_launcher_state() -> (
    ApprovedPaperRunLauncherState
):
    path = (
        APPROVED_PAPER_RUN_LAUNCHER_OUTPUT_DIRECTORY
        / "approved_paper_run_launcher_latest.json"
    )
    if not path.exists():
        return empty_launcher_state()

    payload = read_json_file(path)
    state_payload = payload.get("launcher_state")
    if not isinstance(state_payload, dict):
        raise ValueError(
            "Latest 파일에 Launcher State가 없습니다."
        )
    return launcher_state_from_dict(state_payload)


def validate_executor_result(
    executor_result: Any,
) -> tuple[bool, list[str]]:
    """
    실행기 결과에 실거래 신호가 없는지 검사합니다.

    dict 또는 to_dict()를 제공하는 Result를 지원합니다.
    """

    if hasattr(executor_result, "to_dict"):
        payload = executor_result.to_dict()
    elif isinstance(executor_result, dict):
        payload = executor_result
    else:
        return (
            False,
            ["Paper Executor 결과 형식을 검사할 수 없습니다."],
        )

    if not isinstance(payload, dict):
        return (
            False,
            ["Paper Executor 결과가 dict가 아닙니다."],
        )

    errors: list[str] = []
    unsafe_true_fields = (
        "broker_api_called",
        "broker_order_created",
        "live_order_created",
        "live_execution_authorized",
        "automatic_execution_authorized",
    )
    for name in unsafe_true_fields:
        if payload.get(name) is True:
            errors.append(
                f"Executor 결과의 {name}가 True입니다."
            )

    if payload.get("execution_blocked") is not True:
        errors.append(
            "Executor 결과의 execution_blocked가 True가 아닙니다."
        )

    return (not errors, errors)


def run_approved_paper_run_launcher(
    schedule_plan: PaperTradingSchedulePlan,
    approval_record: ScheduledPaperRunApprovalRecord,
    launch_actor: str,
    launch_note: str,
    launch_text: str,
    launched_at: str | datetime,
    paper_run_executor: Callable[
        [PaperTradingSchedulePlan],
        Any,
    ],
    launcher_state: (
        ApprovedPaperRunLauncherState
        | None
    ) = None,
    launcher_policy: (
        ApprovedPaperRunLauncherPolicy
        | None
    ) = None,
) -> ApprovedPaperRunLauncherResult:
    """
    승인된 Plan을 사용자 요청으로 Paper Executor에 전달합니다.

    이 함수는 Broker API 또는 Live 주문을 직접 호출하지 않습니다.
    """

    policy = (
        launcher_policy
        if launcher_policy is not None
        else ApprovedPaperRunLauncherPolicy()
    )
    state = (
        launcher_state
        if launcher_state is not None
        else load_latest_launcher_state()
    )

    policy_valid, policy_errors = (
        validate_launcher_policy(policy)
    )
    approval_valid, approval_errors = (
        validate_approval_record(
            approval_record
        )
    )
    plan_valid, plan_errors = (
        validate_plan_match(
            schedule_plan,
            approval_record,
        )
    )
    input_valid, input_errors = (
        validate_launch_input(
            launch_actor,
            launch_note,
            launch_text,
            policy,
        )
    )
    state_valid, state_errors = (
        validate_launcher_state(state)
    )

    timing_valid = False
    timing_errors: list[str] = []
    parsed_launched_at: datetime | None = None
    try:
        parsed_launched_at = parse_datetime(
            launched_at,
            "Launched At",
        )
        timing_valid, timing_errors = (
            validate_launch_timing(
                approval_record,
                parsed_launched_at,
                policy,
            )
        )
    except (TypeError, ValueError) as error:
        timing_errors.append(str(error))

    existing_approval_ids = {
        record.approval_id
        for record in state.records
    }
    duplicate_detected = bool(
        isinstance(
            approval_record,
            ScheduledPaperRunApprovalRecord,
        )
        and approval_record.approval_id
        in existing_approval_ids
    )
    duplicate_valid = not duplicate_detected

    executor_called = False
    executor_result: Any = None
    executor_valid = False
    executor_errors: list[str] = []

    preflight_passed = bool(
        policy_valid
        and approval_valid
        and plan_valid
        and input_valid
        and timing_valid
        and state_valid
        and duplicate_valid
        and callable(paper_run_executor)
    )

    if preflight_passed:
        try:
            executor_called = True
            executor_result = paper_run_executor(
                schedule_plan
            )
            executor_valid, executor_errors = (
                validate_executor_result(
                    executor_result
                )
            )
        except Exception as error:
            executor_errors.append(
                f"Paper Executor 실행 실패: {error}"
            )

    if not policy_valid or not state_valid:
        launch_status = "FAILED"
        launch_status_label = (
            "Launcher Policy 또는 State 검사 실패"
        )
    elif duplicate_detected:
        launch_status = "BLOCKED"
        launch_status_label = "중복 Paper Run 실행 차단"
    elif not (
        approval_valid
        and plan_valid
        and input_valid
        and timing_valid
    ):
        launch_status = "BLOCKED"
        launch_status_label = "Paper Run 실행 전 안전검사 차단"
    elif not callable(paper_run_executor):
        launch_status = "FAILED"
        launch_status_label = "Paper Executor가 없습니다"
    elif not executor_valid:
        launch_status = "FAILED"
        launch_status_label = "Paper Executor 결과 검사 실패"
    else:
        launch_status = "COMPLETED"
        launch_status_label = (
            "승인된 Paper Run 수동 실행 완료"
        )

    warnings = [
        *policy_errors,
        *approval_errors,
        *plan_errors,
        *input_errors,
        *timing_errors,
        *state_errors,
        *executor_errors,
    ]
    if duplicate_detected:
        warnings.append(
            "동일 Approval ID의 재실행을 차단했습니다."
        )

    reasons: list[str] = []
    if launch_status == "COMPLETED":
        reasons.append(
            "유효한 V11.0 승인과 수동 실행 입력을 확인했습니다."
        )
    elif launch_status == "BLOCKED":
        reasons.append(
            "승인, 계획, 시간, 입력 또는 중복 검사로 실행을 차단했습니다."
        )
    else:
        reasons.append(
            "Launcher 설정 또는 Paper Executor 검사에 실패했습니다."
        )

    record: ApprovedPaperRunLaunchRecord | None = None
    if (
        isinstance(
            approval_record,
            ScheduledPaperRunApprovalRecord,
        )
        and parsed_launched_at is not None
        and not duplicate_detected
    ):
        record = ApprovedPaperRunLaunchRecord(
            launch_id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(),
            approval_id=approval_record.approval_id,
            plan_id=approval_record.plan_id,
            schedule_key=approval_record.schedule_key,
            scheduled_at=approval_record.scheduled_at,
            launch_status=launch_status,
            launch_status_label=launch_status_label,
            launch_actor=(
                launch_actor.strip()
                if isinstance(launch_actor, str)
                else ""
            ),
            launch_note=(
                launch_note.strip()
                if isinstance(launch_note, str)
                else ""
            ),
            launch_text=(
                launch_text.strip()
                if isinstance(launch_text, str)
                else ""
            ),
            launched_at=parsed_launched_at.isoformat(
                timespec="seconds"
            ),
            executor_called=executor_called,
            executor_result_type=(
                type(executor_result).__name__
                if executor_result is not None
                else None
            ),
            executor_checks_passed=executor_valid,
            paper_run_completed=(
                launch_status == "COMPLETED"
            ),
            approval_checks_passed=approval_valid,
            plan_checks_passed=plan_valid,
            timing_checks_passed=timing_valid,
            input_checks_passed=input_valid,
            duplicate_checks_passed=duplicate_valid,
            all_checks_passed=(
                launch_status
                in VALID_LAUNCH_STATUSES
            ),
            automatic_execution_authorized=False,
            execution_blocked=True,
            broker_api_called=False,
            broker_order_created=False,
            live_order_created=False,
            live_execution_authorized=False,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
        )

    state_trimmed = False
    trimmed_record_count = 0
    record_added = record is not None

    if record is not None:
        records = (*state.records, record)
        if (
            len(records)
            > policy.maximum_launch_record_count
        ):
            if policy.trim_oldest_records:
                trimmed_record_count = (
                    len(records)
                    - policy.maximum_launch_record_count
                )
                records = records[
                    trimmed_record_count:
                ]
                state_trimmed = True
            else:
                warnings.append(
                    "Maximum Launch Record Count를 초과했습니다."
                )
                records = state.records
                record = None
                record_added = False

        updated_state = build_launcher_state(
            records=tuple(records),
            launcher_state_id=(
                state.launcher_state_id
            ),
            created_at=state.created_at,
        )
    else:
        updated_state = state

    updated_state_valid, updated_errors = (
        validate_launcher_state(
            updated_state
        )
    )
    warnings.extend(updated_errors)

    all_checks_passed = bool(
        updated_state_valid
        and launch_status in VALID_LAUNCH_STATUSES
        and (
            record_added
            or duplicate_detected
        )
    )

    if launch_status == "COMPLETED":
        next_actions = [
            "Paper Run 결과를 V10.7 Ledger에 기록합니다.",
            "V10.8 Session Summary와 Risk를 다시 계산합니다.",
        ]
    else:
        next_actions = [
            "Warnings에서 실행 차단 원인을 확인합니다.",
            "새 승인 없이 자동 재실행하지 않습니다.",
        ]

    warnings.extend(
        [
            "V11.1은 승인된 Paper Run만 수동으로 실행합니다.",
            "실제 Broker API와 Live Execution은 허용하지 않습니다.",
        ]
    )

    result = ApprovedPaperRunLauncherResult(
        version="V11.1",
        created_at=datetime.now().isoformat(),
        launcher_result_id=str(uuid.uuid4()),
        launcher_state_id=(
            updated_state.launcher_state_id
        ),
        launch_id=(
            record.launch_id
            if record is not None
            else None
        ),
        approval_id=(
            approval_record.approval_id
            if isinstance(
                approval_record,
                ScheduledPaperRunApprovalRecord,
            )
            else None
        ),
        plan_id=(
            schedule_plan.plan_id
            if isinstance(
                schedule_plan,
                PaperTradingSchedulePlan,
            )
            else None
        ),
        launch_status=launch_status,
        launch_status_label=launch_status_label,
        executor_called=executor_called,
        executor_result=executor_result,
        paper_run_completed=(
            launch_status == "COMPLETED"
        ),
        duplicate_detected=duplicate_detected,
        record_added=record_added,
        state_trimmed=state_trimmed,
        trimmed_record_count=trimmed_record_count,
        policy_checks_passed=policy_valid,
        approval_checks_passed=approval_valid,
        plan_checks_passed=plan_valid,
        timing_checks_passed=timing_valid,
        input_checks_passed=input_valid,
        duplicate_checks_passed=duplicate_valid,
        executor_checks_passed=executor_valid,
        state_checks_passed=updated_state_valid,
        all_checks_passed=all_checks_passed,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        launcher_policy=policy,
        launch_record=record,
        launcher_state=updated_state,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_approved_paper_run_launcher(result)
    return result


def save_approved_paper_run_launcher(
    result: ApprovedPaperRunLauncherResult,
) -> tuple[Path, Path]:
    directory = (
        APPROVED_PAPER_RUN_LAUNCHER_OUTPUT_DIRECTORY
    )
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"approved_paper_run_launcher_{timestamp}.json"
    )
    latest_path = directory / (
        "approved_paper_run_launcher_latest.json"
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    return (report_path, latest_path)


def load_latest_approved_paper_run_launcher() -> (
    dict[str, Any]
):
    path = (
        APPROVED_PAPER_RUN_LAUNCHER_OUTPUT_DIRECTORY
        / "approved_paper_run_launcher_latest.json"
    )
    return read_json_file(path)


def print_approved_paper_run_launcher(
    result: ApprovedPaperRunLauncherResult,
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("V11.1 APPROVED PAPER RUN LAUNCHER")
    print("=" * line_length)
    print(
        f"Launch status                 : "
        f"{result.launch_status}"
    )
    print(
        f"Launch status label           : "
        f"{result.launch_status_label}"
    )
    print(
        f"Approval ID                   : "
        f"{result.approval_id}"
    )
    print(
        f"Plan ID                       : "
        f"{result.plan_id}"
    )
    print(
        f"Executor called               : "
        f"{result.executor_called}"
    )
    print(
        f"Paper run completed           : "
        f"{result.paper_run_completed}"
    )
    print()
    print("VALIDATION")
    print("-" * line_length)
    print(
        f"Approval checks passed        : "
        f"{result.approval_checks_passed}"
    )
    print(
        f"Plan checks passed            : "
        f"{result.plan_checks_passed}"
    )
    print(
        f"Timing checks passed          : "
        f"{result.timing_checks_passed}"
    )
    print(
        f"Input checks passed           : "
        f"{result.input_checks_passed}"
    )
    print(
        f"Duplicate checks passed       : "
        f"{result.duplicate_checks_passed}"
    )
    print(
        f"Executor checks passed        : "
        f"{result.executor_checks_passed}"
    )
    print(
        f"All checks passed             : "
        f"{result.all_checks_passed}"
    )
    print()
    print("EXECUTION SAFETY")
    print("-" * line_length)
    print(
        f"Execution blocked             : "
        f"{result.execution_blocked}"
    )
    print(
        f"Broker API called             : "
        f"{result.broker_api_called}"
    )
    print(
        f"Broker order created          : "
        f"{result.broker_order_created}"
    )
    print(
        f"Live order created            : "
        f"{result.live_order_created}"
    )
    print(
        f"Live execution authorized     : "
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

    print()
    print("FILES")
    print("-" * line_length)
    print(
        f"Report file                   : "
        f"{result.report_path or 'Not saved yet'}"
    )
    print(
        f"Latest file                   : "
        f"{result.latest_path or 'Not saved yet'}"
    )
    print("=" * line_length)
    print(
        "주의: V11.1은 Paper Executor만 수동 호출하며 "
        "실제 Broker 주문을 허용하지 않습니다."
    )
