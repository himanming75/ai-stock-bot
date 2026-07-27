import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import Any

from backtest.paper_trading_session_summary import (
    PaperTradingSessionSummaryResult,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_TRADING_SCHEDULE_PLANNER_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_trading_schedule_planner"
)


VALID_PLAN_STATUSES = {
    "PLANNED",
    "REVIEW_REQUIRED",
    "BLOCKED",
    "FAILED",
}


VALID_PLAN_ACTIONS = {
    "QUEUE",
    "REVIEW",
    "SKIP",
    "BLOCK",
}


@dataclass(frozen=True)
class PaperTradingSchedulePlannerPolicy:
    """
    V10.9 Paper Trading Schedule Planner 정책입니다.

    실제 주문을 실행하지 않고 안전한 Paper 실행 계획만 생성합니다.
    모든 시간은 미국 동부시간(ET) 기준으로 해석합니다.
    """

    timezone_name: str = "America/New_York"
    earliest_run_time: str = "09:35"
    latest_run_time: str = "15:45"

    allowed_weekdays: tuple[
        int,
        ...,
    ] = (
        0,
        1,
        2,
        3,
        4,
    )

    minimum_symbol_count: int = 1
    maximum_symbol_count: int = 50
    reject_duplicate_symbols: bool = False

    require_ready_session: bool = True
    allow_warning_session: bool = False

    reject_duplicate_schedule: bool = True
    maximum_plan_count: int = 1_000
    trim_oldest_plans: bool = True

    require_manual_launch: bool = True
    automatic_execution_disabled: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["allowed_weekdays"] = list(
            self.allowed_weekdays
        )
        return payload


@dataclass(frozen=True)
class PaperTradingSchedulePlan:
    """
    한 번의 Paper Trading 예정 실행입니다.
    """

    plan_id: str
    created_at: str

    schedule_key: str
    scheduled_at: str
    scheduled_date: str
    scheduled_time: str
    timezone_name: str
    weekday: int
    weekday_label: str

    requested_symbols: tuple[
        str,
        ...,
    ]
    normalized_symbols: tuple[
        str,
        ...,
    ]
    duplicate_symbols: tuple[
        str,
        ...,
    ]

    requested_symbol_count: int
    unique_symbol_count: int

    plan_status: str
    plan_status_label: str
    plan_action: str
    plan_action_label: str

    source_summary_id: str
    source_session_status: str
    source_session_action: str

    weekday_allowed: bool
    time_allowed: bool
    symbol_checks_passed: bool
    session_checks_passed: bool
    duplicate_checks_passed: bool
    all_checks_passed: bool

    manual_launch_required: bool
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
        payload["requested_symbols"] = list(
            self.requested_symbols
        )
        payload["normalized_symbols"] = list(
            self.normalized_symbols
        )
        payload["duplicate_symbols"] = list(
            self.duplicate_symbols
        )
        payload["reasons"] = list(self.reasons)
        payload["warnings"] = list(
            self.warnings
        )
        return payload


@dataclass(frozen=True)
class PaperTradingScheduleState:
    """
    누적 Schedule Plan 상태입니다.
    """

    schedule_state_id: str
    created_at: str
    updated_at: str

    plan_count: int
    planned_count: int
    review_required_count: int
    blocked_count: int
    failed_count: int

    plans: tuple[
        PaperTradingSchedulePlan,
        ...,
    ] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["plans"] = [
            plan.to_dict()
            for plan in self.plans
        ]
        return payload


@dataclass
class PaperTradingSchedulePlannerResult:
    """
    V10.9 Schedule Planner 갱신 결과입니다.
    """

    version: str
    created_at: str

    planner_result_id: str
    schedule_state_id: str

    planner_status: str
    planner_status_label: str

    schedule_key: str | None
    plan_id: str | None

    plan_added: bool
    duplicate_detected: bool
    state_trimmed: bool
    trimmed_plan_count: int

    previous_plan_count: int
    current_plan_count: int

    policy_checks_passed: bool
    input_checks_passed: bool
    session_checks_passed: bool
    schedule_checks_passed: bool
    duplicate_checks_passed: bool
    state_checks_passed: bool
    all_checks_passed: bool

    manual_launch_required: bool
    automatic_execution_authorized: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    planner_policy: (
        PaperTradingSchedulePlannerPolicy
    )
    schedule_plan: (
        PaperTradingSchedulePlan
        | None
    )
    schedule_state: (
        PaperTradingScheduleState
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
        payload["planner_policy"] = (
            self.planner_policy.to_dict()
        )
        payload["schedule_plan"] = (
            self.schedule_plan.to_dict()
            if self.schedule_plan is not None
            else None
        )
        payload["schedule_state"] = (
            self.schedule_state.to_dict()
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


def parse_clock_time(
    value: str,
) -> time:
    """
    HH:MM 형식의 시간을 읽습니다.
    """

    if not isinstance(value, str):
        raise TypeError(
            "시간은 HH:MM 문자열이어야 합니다."
        )

    try:
        parsed = datetime.strptime(
            value.strip(),
            "%H:%M",
        )
    except ValueError as error:
        raise ValueError(
            f"시간 형식이 올바르지 않습니다: {value}"
        ) from error

    return parsed.time()


def parse_scheduled_at(
    value: str | datetime,
) -> datetime:
    """
    ISO DateTime 또는 datetime을 읽습니다.

    Timezone 정보가 없는 값은 Policy의 ET 시간으로 해석합니다.
    """

    if isinstance(value, datetime):
        return value

    if not isinstance(value, str):
        raise TypeError(
            "Scheduled At은 ISO 문자열 또는 datetime이어야 합니다."
        )

    try:
        return datetime.fromisoformat(
            value.strip()
        )
    except ValueError as error:
        raise ValueError(
            f"Scheduled At 형식이 올바르지 않습니다: {value}"
        ) from error


def normalize_symbols(
    symbols: list[str] | tuple[str, ...],
) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    """
    Symbol을 대문자로 정규화하고 중복을 분리합니다.
    """

    if not isinstance(
        symbols,
        (list, tuple),
    ):
        raise TypeError(
            "Symbols는 List 또는 Tuple이어야 합니다."
        )

    requested = tuple(
        str(symbol).strip().upper()
        for symbol in symbols
    )

    if not requested:
        raise ValueError(
            "Symbol 목록이 비어 있습니다."
        )

    if any(
        not symbol
        for symbol in requested
    ):
        raise ValueError(
            "비어 있는 Symbol이 포함되어 있습니다."
        )

    normalized: list[str] = []
    duplicates: list[str] = []

    for symbol in requested:
        if symbol in normalized:
            if symbol not in duplicates:
                duplicates.append(symbol)
        else:
            normalized.append(symbol)

    return (
        requested,
        tuple(normalized),
        tuple(duplicates),
    )


def validate_schedule_planner_policy(
    policy: PaperTradingSchedulePlannerPolicy,
) -> tuple[bool, list[str]]:
    """
    V10.9 Planner Policy를 검사합니다.
    """

    if not isinstance(
        policy,
        PaperTradingSchedulePlannerPolicy,
    ):
        return (
            False,
            [
                (
                    "Policy가 "
                    "PaperTradingSchedulePlannerPolicy "
                    "형식이 아닙니다."
                )
            ],
        )

    errors: list[str] = []

    if (
        not isinstance(
            policy.timezone_name,
            str,
        )
        or not policy.timezone_name.strip()
    ):
        errors.append(
            "Timezone Name이 비어 있습니다."
        )

    try:
        earliest = parse_clock_time(
            policy.earliest_run_time
        )
        latest = parse_clock_time(
            policy.latest_run_time
        )

        if earliest >= latest:
            errors.append(
                "Earliest Run Time은 Latest Run Time보다 빨라야 합니다."
            )
    except (TypeError, ValueError) as error:
        errors.append(str(error))

    if not isinstance(
        policy.allowed_weekdays,
        tuple,
    ):
        errors.append(
            "Allowed Weekdays는 Tuple이어야 합니다."
        )
    elif (
        not policy.allowed_weekdays
        or any(
            not isinstance(day, int)
            or day < 0
            or day > 6
            for day in policy.allowed_weekdays
        )
    ):
        errors.append(
            "Allowed Weekdays는 0~6의 int 목록이어야 합니다."
        )

    if (
        not isinstance(
            policy.minimum_symbol_count,
            int,
        )
        or policy.minimum_symbol_count <= 0
    ):
        errors.append(
            "Minimum Symbol Count는 0보다 큰 int여야 합니다."
        )

    if (
        not isinstance(
            policy.maximum_symbol_count,
            int,
        )
        or policy.maximum_symbol_count <= 0
    ):
        errors.append(
            "Maximum Symbol Count는 0보다 큰 int여야 합니다."
        )

    if (
        isinstance(
            policy.minimum_symbol_count,
            int,
        )
        and isinstance(
            policy.maximum_symbol_count,
            int,
        )
        and policy.minimum_symbol_count
        > policy.maximum_symbol_count
    ):
        errors.append(
            "Minimum Symbol Count가 Maximum보다 클 수 없습니다."
        )

    if (
        not isinstance(
            policy.maximum_plan_count,
            int,
        )
        or policy.maximum_plan_count <= 0
    ):
        errors.append(
            "Maximum Plan Count는 0보다 큰 int여야 합니다."
        )

    boolean_fields = {
        "reject_duplicate_symbols": (
            policy.reject_duplicate_symbols
        ),
        "require_ready_session": (
            policy.require_ready_session
        ),
        "allow_warning_session": (
            policy.allow_warning_session
        ),
        "reject_duplicate_schedule": (
            policy.reject_duplicate_schedule
        ),
        "trim_oldest_plans": (
            policy.trim_oldest_plans
        ),
        "require_manual_launch": (
            policy.require_manual_launch
        ),
        "automatic_execution_disabled": (
            policy.automatic_execution_disabled
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

    if not policy.reject_duplicate_schedule:
        errors.append(
            "V10.9에서는 Duplicate Schedule 차단이 필수입니다."
        )

    if not policy.require_manual_launch:
        errors.append(
            "V10.9에서는 Manual Launch가 필수입니다."
        )

    if not policy.automatic_execution_disabled:
        errors.append(
            "V10.9에서는 Automatic Execution이 차단되어야 합니다."
        )

    if not policy.paper_only:
        errors.append(
            "V10.9에서는 Paper Only가 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V10.9에서는 Live Execution Disabled가 "
            "True여야 합니다."
        )

    return (not errors, errors)


def validate_session_summary(
    summary: PaperTradingSessionSummaryResult,
    policy: PaperTradingSchedulePlannerPolicy,
) -> tuple[bool, bool, list[str]]:
    """
    V10.8 Summary가 계획 생성에 적합한지 검사합니다.

    반환값:
    - checks_passed
    - review_required
    - errors
    """

    errors: list[str] = []
    review_required = False

    if not isinstance(
        summary,
        PaperTradingSessionSummaryResult,
    ):
        return (
            False,
            False,
            [
                (
                    "Session Summary가 "
                    "PaperTradingSessionSummaryResult "
                    "형식이 아닙니다."
                )
            ],
        )

    if summary.version != "V10.8":
        errors.append(
            "Session Summary 버전이 V10.8이 아닙니다."
        )

    if not summary.all_checks_passed:
        errors.append(
            "Session Summary All Checks가 실패했습니다."
        )

    if summary.execution_blocked is not True:
        errors.append(
            "Session Summary Execution이 차단되지 않았습니다."
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
            "Session Summary의 실거래 안전 상태가 올바르지 않습니다."
        )

    if summary.session_status == "READY":
        pass
    elif (
        summary.session_status == "WARNING"
        and policy.allow_warning_session
    ):
        review_required = True
    else:
        errors.append(
            (
                "현재 Session Status에서는 "
                "새 Schedule을 만들 수 없습니다: "
                f"{summary.session_status}"
            )
        )

    if (
        policy.require_ready_session
        and summary.session_status != "READY"
        and not (
            summary.session_status == "WARNING"
            and policy.allow_warning_session
        )
    ):
        errors.append(
            "Policy가 READY Session을 요구합니다."
        )

    return (
        not errors,
        review_required,
        errors,
    )


def create_schedule_key(
    scheduled_at: datetime,
    normalized_symbols: tuple[
        str,
        ...,
    ],
) -> str:
    """
    동일 시각과 동일 종목 조합을 중복으로 판단합니다.
    """

    symbols_key = ",".join(
        normalized_symbols
    )

    return (
        f"{scheduled_at.isoformat(timespec='minutes')}"
        f"|{symbols_key}"
    )


def plan_action_label(
    action: str,
) -> str:
    labels = {
        "QUEUE": "수동 실행 대기열에 추가",
        "REVIEW": "수동 검토 후 실행",
        "SKIP": "중복 계획 건너뜀",
        "BLOCK": "계획 생성 차단",
    }
    return labels[action]


def empty_schedule_state() -> (
    PaperTradingScheduleState
):
    now = datetime.now().isoformat()

    return PaperTradingScheduleState(
        schedule_state_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        plan_count=0,
        planned_count=0,
        review_required_count=0,
        blocked_count=0,
        failed_count=0,
        plans=(),
    )


def build_schedule_state(
    plans: tuple[
        PaperTradingSchedulePlan,
        ...,
    ],
    schedule_state_id: str | None = None,
    created_at: str | None = None,
) -> PaperTradingScheduleState:
    return PaperTradingScheduleState(
        schedule_state_id=(
            schedule_state_id
            or str(uuid.uuid4())
        ),
        created_at=(
            created_at
            or datetime.now().isoformat()
        ),
        updated_at=datetime.now().isoformat(),
        plan_count=len(plans),
        planned_count=sum(
            plan.plan_status == "PLANNED"
            for plan in plans
        ),
        review_required_count=sum(
            plan.plan_status
            == "REVIEW_REQUIRED"
            for plan in plans
        ),
        blocked_count=sum(
            plan.plan_status == "BLOCKED"
            for plan in plans
        ),
        failed_count=sum(
            plan.plan_status == "FAILED"
            for plan in plans
        ),
        plans=plans,
    )


def validate_schedule_state(
    state: PaperTradingScheduleState,
) -> tuple[bool, list[str]]:
    """
    Schedule State 집계 및 중복 여부를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        state,
        PaperTradingScheduleState,
    ):
        return (
            False,
            [
                (
                    "Schedule State가 "
                    "PaperTradingScheduleState "
                    "형식이 아닙니다."
                )
            ],
        )

    rebuilt = build_schedule_state(
        plans=state.plans,
        schedule_state_id=(
            state.schedule_state_id
        ),
        created_at=state.created_at,
    )

    count_fields = (
        "plan_count",
        "planned_count",
        "review_required_count",
        "blocked_count",
        "failed_count",
    )

    for field_name in count_fields:
        if (
            getattr(state, field_name)
            != getattr(rebuilt, field_name)
        ):
            errors.append(
                f"Schedule 집계값 {field_name}가 Plan 목록과 다릅니다."
            )

    schedule_keys = [
        plan.schedule_key
        for plan in state.plans
    ]

    if (
        len(schedule_keys)
        != len(set(schedule_keys))
    ):
        errors.append(
            "Schedule State에 중복 Schedule Key가 있습니다."
        )

    for plan in state.plans:
        if plan.plan_status not in VALID_PLAN_STATUSES:
            errors.append(
                f"허용되지 않은 Plan Status입니다: {plan.plan_status}"
            )

        if plan.plan_action not in VALID_PLAN_ACTIONS:
            errors.append(
                f"허용되지 않은 Plan Action입니다: {plan.plan_action}"
            )

        if not plan.execution_blocked:
            errors.append(
                f"{plan.plan_id}: Execution이 차단되지 않았습니다."
            )

        if any(
            (
                plan.broker_api_called,
                plan.broker_order_created,
                plan.live_order_created,
                plan.live_execution_authorized,
                plan.automatic_execution_authorized,
            )
        ):
            errors.append(
                f"{plan.plan_id}: 실행 안전 상태가 올바르지 않습니다."
            )

    return (not errors, errors)


def schedule_plan_from_dict(
    payload: dict[str, Any],
) -> PaperTradingSchedulePlan:
    values = dict(payload)
    values["requested_symbols"] = tuple(
        values.get(
            "requested_symbols",
            [],
        )
    )
    values["normalized_symbols"] = tuple(
        values.get(
            "normalized_symbols",
            [],
        )
    )
    values["duplicate_symbols"] = tuple(
        values.get(
            "duplicate_symbols",
            [],
        )
    )
    values["reasons"] = tuple(
        values.get("reasons", [])
    )
    values["warnings"] = tuple(
        values.get("warnings", [])
    )

    return PaperTradingSchedulePlan(
        **values
    )


def schedule_state_from_dict(
    payload: dict[str, Any],
) -> PaperTradingScheduleState:
    if not isinstance(payload, dict):
        raise TypeError(
            "Schedule State Payload는 Dictionary여야 합니다."
        )

    plans_payload = payload.get(
        "plans",
        [],
    )

    if not isinstance(plans_payload, list):
        raise ValueError(
            "Schedule Plans가 List가 아닙니다."
        )

    plans = tuple(
        schedule_plan_from_dict(plan)
        for plan in plans_payload
    )

    return build_schedule_state(
        plans=plans,
        schedule_state_id=str(
            payload.get(
                "schedule_state_id",
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


def load_latest_schedule_state(
    default_state: (
        PaperTradingScheduleState
        | None
    ) = None,
) -> PaperTradingScheduleState:
    latest_path = (
        PAPER_TRADING_SCHEDULE_PLANNER_OUTPUT_DIRECTORY
        / "paper_trading_schedule_planner_latest.json"
    )

    if not latest_path.exists():
        return (
            default_state
            if default_state is not None
            else empty_schedule_state()
        )

    payload = read_json_file(
        latest_path
    )

    state_payload = payload.get(
        "schedule_state",
        payload,
    )

    return schedule_state_from_dict(
        state_payload
    )


def run_paper_trading_schedule_planner(
    scheduled_at: str | datetime,
    symbols: list[str] | tuple[str, ...],
    session_summary: (
        PaperTradingSessionSummaryResult
    ),
    schedule_state: (
        PaperTradingScheduleState
        | None
    ) = None,
    planner_policy: (
        PaperTradingSchedulePlannerPolicy
        | None
    ) = None,
) -> PaperTradingSchedulePlannerResult:
    """
    Paper Trading 실행 계획을 생성합니다.

    계획만 기록하며 실제 자동 실행이나 주문은 수행하지 않습니다.
    """

    policy = (
        planner_policy
        if planner_policy is not None
        else PaperTradingSchedulePlannerPolicy()
    )

    policy_valid, policy_errors = (
        validate_schedule_planner_policy(
            policy
        )
    )

    input_errors: list[str] = []

    try:
        parsed_schedule = (
            parse_scheduled_at(
                scheduled_at
            )
        )
    except Exception as error:
        parsed_schedule = None
        input_errors.append(str(error))

    try:
        (
            requested_symbols,
            normalized_symbols,
            duplicate_symbols,
        ) = normalize_symbols(symbols)
    except Exception as error:
        requested_symbols = ()
        normalized_symbols = ()
        duplicate_symbols = ()
        input_errors.append(str(error))

    symbol_checks_passed = bool(
        normalized_symbols
        and len(normalized_symbols)
        >= policy.minimum_symbol_count
        and len(normalized_symbols)
        <= policy.maximum_symbol_count
        and not (
            policy.reject_duplicate_symbols
            and duplicate_symbols
        )
    )

    if (
        normalized_symbols
        and len(normalized_symbols)
        < policy.minimum_symbol_count
    ):
        input_errors.append(
            "고유 Symbol 수가 Minimum보다 적습니다."
        )

    if (
        len(normalized_symbols)
        > policy.maximum_symbol_count
    ):
        input_errors.append(
            "고유 Symbol 수가 Maximum을 초과했습니다."
        )

    if (
        policy.reject_duplicate_symbols
        and duplicate_symbols
    ):
        input_errors.append(
            (
                "중복 Symbol이 허용되지 않습니다: "
                f"{', '.join(duplicate_symbols)}"
            )
        )

    (
        session_valid,
        session_review_required,
        session_errors,
    ) = validate_session_summary(
        session_summary,
        policy,
    )

    working_state = (
        schedule_state
        if schedule_state is not None
        else load_latest_schedule_state()
    )

    state_valid, state_errors = (
        validate_schedule_state(
            working_state
        )
    )

    weekday_allowed = False
    time_allowed = False
    schedule_key: str | None = None

    if parsed_schedule is not None:
        weekday_allowed = (
            parsed_schedule.weekday()
            in policy.allowed_weekdays
        )

        earliest = parse_clock_time(
            policy.earliest_run_time
        )
        latest = parse_clock_time(
            policy.latest_run_time
        )
        schedule_clock = (
            parsed_schedule.time()
            .replace(
                second=0,
                microsecond=0,
            )
        )
        time_allowed = (
            earliest
            <= schedule_clock
            <= latest
        )

        schedule_key = create_schedule_key(
            parsed_schedule,
            normalized_symbols,
        )

    existing_keys = {
        plan.schedule_key
        for plan in working_state.plans
    }

    duplicate_detected = bool(
        schedule_key
        and schedule_key in existing_keys
    )
    duplicate_checks_passed = (
        not duplicate_detected
    )

    input_checks_passed = bool(
        not input_errors
        and parsed_schedule is not None
        and symbol_checks_passed
    )
    schedule_checks_passed = bool(
        parsed_schedule is not None
        and weekday_allowed
        and time_allowed
    )

    reasons: list[str] = []
    warnings: list[str] = []
    warnings.extend(policy_errors)
    warnings.extend(input_errors)
    warnings.extend(session_errors)
    warnings.extend(state_errors)

    if duplicate_symbols:
        warnings.append(
            (
                "중복 제거된 Symbol: "
                f"{', '.join(duplicate_symbols)}"
            )
        )

    if parsed_schedule is not None:
        if not weekday_allowed:
            warnings.append(
                "주말 또는 허용되지 않은 요일입니다."
            )

        if not time_allowed:
            warnings.append(
                (
                    "허용된 Paper 실행 시간 "
                    f"{policy.earliest_run_time}~"
                    f"{policy.latest_run_time} ET 밖입니다."
                )
            )

    if duplicate_detected:
        warnings.append(
            "동일 시각과 종목 조합의 Schedule이 이미 있습니다."
        )

    schedule_plan: (
        PaperTradingSchedulePlan
        | None
    ) = None

    if not policy_valid or not state_valid:
        planner_status = "FAILED"
        planner_status_label = (
            "Planner Policy 또는 State 검사 실패"
        )
        plan_status = "FAILED"
        plan_action = "BLOCK"
    elif not input_checks_passed:
        planner_status = "FAILED"
        planner_status_label = (
            "Schedule 입력 검사 실패"
        )
        plan_status = "FAILED"
        plan_action = "BLOCK"
    elif duplicate_detected:
        planner_status = "BLOCKED"
        planner_status_label = (
            "중복 Schedule 차단"
        )
        plan_status = "BLOCKED"
        plan_action = "SKIP"
    elif not session_valid:
        planner_status = "BLOCKED"
        planner_status_label = (
            "Session 상태로 Schedule 차단"
        )
        plan_status = "BLOCKED"
        plan_action = "BLOCK"
    elif not schedule_checks_passed:
        planner_status = "BLOCKED"
        planner_status_label = (
            "요일 또는 시간 기준으로 Schedule 차단"
        )
        plan_status = "BLOCKED"
        plan_action = "BLOCK"
    elif session_review_required:
        planner_status = "REVIEW_REQUIRED"
        planner_status_label = (
            "수동 검토가 필요한 Schedule"
        )
        plan_status = "REVIEW_REQUIRED"
        plan_action = "REVIEW"
    else:
        planner_status = "PLANNED"
        planner_status_label = (
            "Paper Trading 실행 계획 생성 완료"
        )
        plan_status = "PLANNED"
        plan_action = "QUEUE"

    plan_added = False
    state_trimmed = False
    trimmed_plan_count = 0
    previous_plan_count = (
        working_state.plan_count
    )

    can_add_plan = bool(
        planner_status
        in {
            "PLANNED",
            "REVIEW_REQUIRED",
        }
        and schedule_key is not None
        and parsed_schedule is not None
        and not duplicate_detected
    )

    if can_add_plan:
        weekday_labels = (
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        )

        plan_reasons = [
            (
                f"{parsed_schedule.isoformat(timespec='minutes')} "
                f"{policy.timezone_name} 실행 계획입니다."
            ),
            (
                f"고유 Symbol {len(normalized_symbols)}개가 "
                "수동 실행 대기 상태입니다."
            ),
        ]

        plan_warnings = [
            (
                "미국 증시 휴장일 Calendar는 V10.9에서 "
                "자동 판정하지 않습니다."
            ),
            (
                "실행 전에 거래일과 시장 상태를 수동 확인해야 합니다."
            ),
        ]
        plan_warnings.extend(warnings)

        schedule_plan = (
            PaperTradingSchedulePlan(
                plan_id=str(uuid.uuid4()),
                created_at=(
                    datetime.now().isoformat()
                ),
                schedule_key=schedule_key,
                scheduled_at=(
                    parsed_schedule
                    .isoformat(
                        timespec="minutes"
                    )
                ),
                scheduled_date=(
                    parsed_schedule
                    .date()
                    .isoformat()
                ),
                scheduled_time=(
                    parsed_schedule
                    .strftime("%H:%M")
                ),
                timezone_name=(
                    policy.timezone_name
                ),
                weekday=(
                    parsed_schedule.weekday()
                ),
                weekday_label=(
                    weekday_labels[
                        parsed_schedule.weekday()
                    ]
                ),
                requested_symbols=(
                    requested_symbols
                ),
                normalized_symbols=(
                    normalized_symbols
                ),
                duplicate_symbols=(
                    duplicate_symbols
                ),
                requested_symbol_count=len(
                    requested_symbols
                ),
                unique_symbol_count=len(
                    normalized_symbols
                ),
                plan_status=plan_status,
                plan_status_label=(
                    planner_status_label
                ),
                plan_action=plan_action,
                plan_action_label=(
                    plan_action_label(
                        plan_action
                    )
                ),
                source_summary_id=(
                    session_summary
                    .session_summary_id
                ),
                source_session_status=(
                    session_summary
                    .session_status
                ),
                source_session_action=(
                    session_summary
                    .session_action
                ),
                weekday_allowed=(
                    weekday_allowed
                ),
                time_allowed=time_allowed,
                symbol_checks_passed=(
                    symbol_checks_passed
                ),
                session_checks_passed=(
                    session_valid
                ),
                duplicate_checks_passed=(
                    duplicate_checks_passed
                ),
                all_checks_passed=True,
                manual_launch_required=True,
                automatic_execution_authorized=False,
                execution_blocked=True,
                broker_api_called=False,
                broker_order_created=False,
                live_order_created=False,
                live_execution_authorized=False,
                reasons=tuple(
                    plan_reasons
                ),
                warnings=tuple(
                    plan_warnings
                ),
            )
        )

        updated_plans = (
            *working_state.plans,
            schedule_plan,
        )

        if (
            len(updated_plans)
            > policy.maximum_plan_count
        ):
            if policy.trim_oldest_plans:
                trimmed_plan_count = (
                    len(updated_plans)
                    - policy.maximum_plan_count
                )
                updated_plans = updated_plans[
                    trimmed_plan_count:
                ]
                state_trimmed = True
            else:
                warnings.append(
                    "Maximum Plan Count를 초과했습니다."
                )
                updated_plans = (
                    working_state.plans
                )
                schedule_plan = None
                can_add_plan = False

        if can_add_plan:
            updated_state = (
                build_schedule_state(
                    plans=tuple(
                        updated_plans
                    ),
                    schedule_state_id=(
                        working_state
                        .schedule_state_id
                    ),
                    created_at=(
                        working_state
                        .created_at
                    ),
                )
            )
            plan_added = True
        else:
            updated_state = working_state
    else:
        updated_state = working_state

    updated_state_valid, updated_state_errors = (
        validate_schedule_state(
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
        and planner_status
        in VALID_PLAN_STATUSES
        and (
            plan_added
            or planner_status
            in {
                "BLOCKED",
                "FAILED",
            }
        )
    )

    if planner_status == "PLANNED":
        reasons.append(
            "Paper Trading 계획을 수동 실행 대기열에 추가했습니다."
        )
        next_actions = [
            "예정일의 미국 증시 휴장 여부를 수동 확인합니다.",
            "예정시간 전에 Session Summary와 Risk를 다시 확인합니다.",
            "사용자가 수동으로 승인한 경우에만 다음 실행 단계로 이동합니다.",
        ]
    elif planner_status == "REVIEW_REQUIRED":
        reasons.append(
            "Session WARNING으로 수동 검토가 필요한 계획을 추가했습니다."
        )
        next_actions = [
            "V10.8 Triggered Rule을 확인합니다.",
            "검토 후 실행 또는 취소를 결정합니다.",
        ]
    elif duplicate_detected:
        reasons.append(
            "동일 Schedule Key가 이미 있어 중복 계획을 차단했습니다."
        )
        next_actions = [
            "기존 Plan을 확인합니다.",
            "다른 시각 또는 종목 조합이 필요한지 검토합니다.",
        ]
    else:
        reasons.append(
            "입력, Session, 요일 또는 시간 검사로 계획을 차단했습니다."
        )
        next_actions = [
            "Warnings와 차단 조건을 확인합니다.",
            "조건을 수정한 후 V10.9 Planner를 다시 실행합니다.",
        ]

    warnings.extend(
        [
            (
                "V10.9는 Schedule Planner이며 "
                "자동 실행기가 아닙니다."
            ),
            (
                "미국 증시 휴장일과 조기 폐장일은 "
                "수동 확인이 필요합니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 "
                "Live Execution은 모두 차단됩니다."
            ),
        ]
    )

    result = PaperTradingSchedulePlannerResult(
        version="V10.9",
        created_at=datetime.now().isoformat(),
        planner_result_id=str(uuid.uuid4()),
        schedule_state_id=(
            updated_state.schedule_state_id
        ),
        planner_status=planner_status,
        planner_status_label=(
            planner_status_label
        ),
        schedule_key=schedule_key,
        plan_id=(
            schedule_plan.plan_id
            if schedule_plan is not None
            else None
        ),
        plan_added=plan_added,
        duplicate_detected=(
            duplicate_detected
        ),
        state_trimmed=state_trimmed,
        trimmed_plan_count=(
            trimmed_plan_count
        ),
        previous_plan_count=(
            previous_plan_count
        ),
        current_plan_count=(
            updated_state.plan_count
        ),
        policy_checks_passed=(
            policy_valid
        ),
        input_checks_passed=(
            input_checks_passed
        ),
        session_checks_passed=(
            session_valid
        ),
        schedule_checks_passed=(
            schedule_checks_passed
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
        manual_launch_required=True,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        planner_policy=policy,
        schedule_plan=schedule_plan,
        schedule_state=updated_state,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_trading_schedule_planner(
        result
    )

    return result


def save_paper_trading_schedule_planner(
    result: PaperTradingSchedulePlannerResult,
) -> tuple[Path, Path]:
    """
    V10.9 Report와 Latest Schedule State를 저장합니다.
    """

    PAPER_TRADING_SCHEDULE_PLANNER_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    report_path = (
        PAPER_TRADING_SCHEDULE_PLANNER_OUTPUT_DIRECTORY
        / (
            "paper_trading_schedule_planner_"
            f"{timestamp}.json"
        )
    )
    latest_path = (
        PAPER_TRADING_SCHEDULE_PLANNER_OUTPUT_DIRECTORY
        / (
            "paper_trading_schedule_planner_"
            "latest.json"
        )
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)

    payload = result.to_dict()

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)

    return (report_path, latest_path)


def load_latest_paper_trading_schedule_planner() -> (
    dict[str, Any]
):
    latest_path = (
        PAPER_TRADING_SCHEDULE_PLANNER_OUTPUT_DIRECTORY
        / (
            "paper_trading_schedule_planner_"
            "latest.json"
        )
    )

    return read_json_file(latest_path)


def print_paper_trading_schedule_planner(
    result: PaperTradingSchedulePlannerResult,
) -> None:
    """
    V10.9 Planner 결과를 터미널에 출력합니다.
    """

    line_length = 140

    print()
    print("=" * line_length)
    print(
        "V10.9 PAPER TRADING SCHEDULE PLANNER"
    )
    print("=" * line_length)

    print(
        f"Planner status                 : "
        f"{result.planner_status}"
    )
    print(
        f"Planner status label           : "
        f"{result.planner_status_label}"
    )
    print(
        f"Planner result ID              : "
        f"{result.planner_result_id}"
    )
    print(
        f"Schedule state ID              : "
        f"{result.schedule_state_id}"
    )
    print(
        f"Schedule key                   : "
        f"{result.schedule_key}"
    )
    print(
        f"Plan ID                        : "
        f"{result.plan_id}"
    )

    print()
    print("PLAN UPDATE")
    print("-" * line_length)

    print(
        f"Plan added                     : "
        f"{result.plan_added}"
    )
    print(
        f"Duplicate detected             : "
        f"{result.duplicate_detected}"
    )
    print(
        f"State trimmed                  : "
        f"{result.state_trimmed}"
    )
    print(
        f"Previous plan count            : "
        f"{result.previous_plan_count}"
    )
    print(
        f"Current plan count             : "
        f"{result.current_plan_count}"
    )

    if result.schedule_plan is not None:
        plan = result.schedule_plan

        print()
        print("SCHEDULE PLAN")
        print("-" * line_length)

        print(
            f"Scheduled at                   : "
            f"{plan.scheduled_at}"
        )
        print(
            f"Timezone                       : "
            f"{plan.timezone_name}"
        )
        print(
            f"Weekday                        : "
            f"{plan.weekday_label}"
        )
        print(
            f"Symbols                        : "
            f"{', '.join(plan.normalized_symbols)}"
        )
        print(
            f"Plan status                    : "
            f"{plan.plan_status}"
        )
        print(
            f"Plan action                    : "
            f"{plan.plan_action}"
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
        f"Session checks passed          : "
        f"{result.session_checks_passed}"
    )
    print(
        f"Schedule checks passed         : "
        f"{result.schedule_checks_passed}"
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
        f"Manual launch required         : "
        f"{result.manual_launch_required}"
    )
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
        "주의: V10.9는 Paper Trading 계획만 생성하며 "
        "실제 또는 자동 주문을 수행하지 않습니다."
    )
