import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from backtest.paper_portfolio_performance_tracker import (
    PaperPortfolioPerformanceResult,
)
from backtest.paper_trading_risk_monitor import (
    PaperTradingRiskMonitorResult,
)
from backtest.post_run_session_refresh import (
    PostRunSessionRefreshResult,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

POST_RUN_PERFORMANCE_RISK_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "post_run_performance_risk_refresh"
)

VALID_REFRESH_STATUSES = {
    "REFRESHED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PostRunPerformanceRiskPolicy:
    """
    V11.4 Post-Run Performance & Risk Refresh 정책입니다.
    """

    require_refreshed_session: bool = True
    require_successful_performance: bool = True
    require_successful_risk: bool = True
    require_matching_portfolio: bool = True
    require_matching_performance_source: bool = True
    reject_duplicate_session_refresh_id: bool = True

    maximum_refresh_delay_minutes: int = 20
    maximum_record_count: int = 10_000
    trim_oldest_records: bool = True

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PostRunPerformanceRiskRecord:
    refresh_id: str
    created_at: str

    session_refresh_id: str
    integration_id: str
    ledger_id: str
    session_summary_id: str
    session_status: str
    session_action: str

    performance_id: str
    portfolio_id: str
    performance_status: str
    current_equity: float
    cumulative_return_percent: float
    maximum_drawdown_percent: float

    risk_monitor_id: str
    risk_status: str
    risk_action: str

    refresh_delay_minutes: float
    performance_builder_called: bool
    risk_builder_called: bool

    session_checks_passed: bool
    performance_checks_passed: bool
    risk_checks_passed: bool
    source_match_checks_passed: bool
    timing_checks_passed: bool
    duplicate_checks_passed: bool
    all_checks_passed: bool

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
class PostRunPerformanceRiskState:
    state_id: str
    created_at: str
    updated_at: str
    record_count: int
    refreshed_count: int
    records: tuple[
        PostRunPerformanceRiskRecord,
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
class PostRunPerformanceRiskResult:
    version: str
    created_at: str

    result_id: str
    state_id: str
    refresh_id: str | None
    session_refresh_id: str | None

    refresh_status: str
    refresh_status_label: str

    performance_builder_called: bool
    risk_builder_called: bool
    performance_refreshed: bool
    risk_refreshed: bool

    performance_id: str | None
    risk_monitor_id: str | None
    risk_status: str | None
    risk_action: str | None

    duplicate_detected: bool
    record_added: bool
    state_trimmed: bool
    trimmed_record_count: int
    previous_record_count: int
    current_record_count: int

    policy_checks_passed: bool
    session_checks_passed: bool
    performance_checks_passed: bool
    risk_checks_passed: bool
    source_match_checks_passed: bool
    timing_checks_passed: bool
    duplicate_checks_passed: bool
    state_checks_passed: bool
    all_checks_passed: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    refresh_policy: PostRunPerformanceRiskPolicy
    performance_result: (
        PaperPortfolioPerformanceResult
        | None
    )
    risk_result: PaperTradingRiskMonitorResult | None
    refresh_record: (
        PostRunPerformanceRiskRecord
        | None
    )
    refresh_state: PostRunPerformanceRiskState

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["refresh_policy"] = (
            self.refresh_policy.to_dict()
        )
        payload["performance_result"] = (
            self.performance_result.to_dict()
            if self.performance_result is not None
            else None
        )
        payload["risk_result"] = (
            self.risk_result.to_dict()
            if self.risk_result is not None
            else None
        )
        payload["refresh_record"] = (
            self.refresh_record.to_dict()
            if self.refresh_record is not None
            else None
        )
        payload["refresh_state"] = (
            self.refresh_state.to_dict()
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


def validate_refresh_policy(
    policy: PostRunPerformanceRiskPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        PostRunPerformanceRiskPolicy,
    ):
        return (
            False,
            ["Performance Risk Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    for name, value in {
        "maximum_refresh_delay_minutes": (
            policy.maximum_refresh_delay_minutes
        ),
        "maximum_record_count": (
            policy.maximum_record_count
        ),
    }.items():
        if (
            not isinstance(value, int)
            or value <= 0
        ):
            errors.append(
                f"{name}는 0보다 큰 int여야 합니다."
            )

    required_true = {
        "require_refreshed_session": (
            policy.require_refreshed_session
        ),
        "require_successful_performance": (
            policy.require_successful_performance
        ),
        "require_successful_risk": (
            policy.require_successful_risk
        ),
        "require_matching_portfolio": (
            policy.require_matching_portfolio
        ),
        "require_matching_performance_source": (
            policy.require_matching_performance_source
        ),
        "reject_duplicate_session_refresh_id": (
            policy.reject_duplicate_session_refresh_id
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }
    for name, value in required_true.items():
        if value is not True:
            errors.append(
                f"{name}는 V11.4에서 True여야 합니다."
            )

    if not isinstance(
        policy.trim_oldest_records,
        bool,
    ):
        errors.append(
            "trim_oldest_records가 bool 형식이 아닙니다."
        )
    return (not errors, errors)


def validate_session_refresh(
    result: PostRunSessionRefreshResult,
) -> tuple[bool, list[str]]:
    if not isinstance(
        result,
        PostRunSessionRefreshResult,
    ):
        return (
            False,
            ["V11.3 Session Refresh Result 형식이 아닙니다."],
        )

    errors: list[str] = []
    if result.version != "V11.3":
        errors.append(
            "Session Refresh 버전이 V11.3이 아닙니다."
        )
    if result.refresh_status != "REFRESHED":
        errors.append(
            "Session Refresh Status가 REFRESHED가 아닙니다."
        )
    if not result.session_refreshed:
        errors.append(
            "Session이 갱신되지 않았습니다."
        )
    if not result.summary_checks_passed:
        errors.append(
            "Session Summary 검사가 실패했습니다."
        )
    if not result.all_checks_passed:
        errors.append(
            "Session Refresh All Checks가 실패했습니다."
        )
    if result.session_summary is None:
        errors.append(
            "Session Summary가 없습니다."
        )
    if not result.refresh_id:
        errors.append("Session Refresh ID가 없습니다.")
    if result.execution_blocked is not True:
        errors.append(
            "Session Refresh Execution 차단 상태가 올바르지 않습니다."
        )
    if any(
        (
            result.broker_api_called,
            result.broker_order_created,
            result.live_order_created,
            result.live_execution_authorized,
        )
    ):
        errors.append(
            "Session Refresh에 실거래 신호가 있습니다."
        )
    return (not errors, errors)


def validate_performance_result(
    result: PaperPortfolioPerformanceResult,
) -> tuple[bool, list[str]]:
    if not isinstance(
        result,
        PaperPortfolioPerformanceResult,
    ):
        return (
            False,
            ["V10.1 Performance Result 형식이 아닙니다."],
        )

    errors: list[str] = []
    if result.version != "V10.1":
        errors.append(
            "Performance 버전이 V10.1이 아닙니다."
        )
    if result.performance_status not in {
        "TRACKED",
        "FIRST_SNAPSHOT",
        "NO_CHANGE",
    }:
        errors.append(
            "Performance Status가 성공 상태가 아닙니다."
        )
    if not result.all_checks_passed:
        errors.append(
            "Performance All Checks가 실패했습니다."
        )
    if result.execution_blocked is not True:
        errors.append(
            "Performance Execution 차단 상태가 올바르지 않습니다."
        )
    if any(
        (
            result.broker_api_called,
            result.broker_order_created,
            result.live_order_created,
            result.live_execution_authorized,
        )
    ):
        errors.append(
            "Performance Result에 실거래 신호가 있습니다."
        )
    return (not errors, errors)


def validate_risk_result(
    result: PaperTradingRiskMonitorResult,
) -> tuple[bool, list[str]]:
    if not isinstance(
        result,
        PaperTradingRiskMonitorResult,
    ):
        return (
            False,
            ["V10.4 Risk Result 형식이 아닙니다."],
        )

    errors: list[str] = []
    if result.version != "V10.4":
        errors.append(
            "Risk Monitor 버전이 V10.4가 아닙니다."
        )
    if result.risk_status not in {
        "SAFE",
        "WARNING",
        "PAUSED",
        "BLOCKED",
    }:
        errors.append(
            "Risk Status가 올바르지 않습니다."
        )
    if result.risk_action not in {
        "ALLOW",
        "WARN",
        "PAUSE",
        "BLOCK",
    }:
        errors.append(
            "Risk Action이 올바르지 않습니다."
        )
    if not result.all_checks_passed:
        errors.append(
            "Risk All Checks가 실패했습니다."
        )
    if result.execution_blocked is not True:
        errors.append(
            "Risk Execution 차단 상태가 올바르지 않습니다."
        )
    if any(
        (
            result.broker_api_called,
            result.broker_order_created,
            result.live_order_created,
            result.live_execution_authorized,
        )
    ):
        errors.append(
            "Risk Result에 실거래 신호가 있습니다."
        )
    return (not errors, errors)


def validate_source_match(
    performance: PaperPortfolioPerformanceResult,
    risk: PaperTradingRiskMonitorResult,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if performance.portfolio_id != risk.portfolio_id:
        errors.append(
            "Performance와 Risk Portfolio ID가 다릅니다."
        )
    if (
        risk.source_performance_id
        != performance.performance_id
    ):
        errors.append(
            "Risk Source Performance ID가 다릅니다."
        )
    if risk.current_equity != performance.current_equity:
        errors.append(
            "Risk와 Performance Current Equity가 다릅니다."
        )
    return (not errors, errors)


def validate_refresh_timing(
    session_refresh: PostRunSessionRefreshResult,
    refreshed_at: datetime,
    policy: PostRunPerformanceRiskPolicy,
) -> tuple[bool, float, list[str]]:
    try:
        source_time = parse_datetime(
            session_refresh.created_at,
            "Session Refresh Created At",
        )
    except (TypeError, ValueError) as error:
        return (False, 0.0, [str(error)])

    if (
        source_time.tzinfo is None
    ) != (
        refreshed_at.tzinfo is None
    ):
        return (
            False,
            0.0,
            ["Session과 Performance Risk 시각의 Timezone 형식이 다릅니다."],
        )

    delay = (
        refreshed_at - source_time
    ).total_seconds() / 60.0
    errors: list[str] = []
    if delay < 0:
        errors.append(
            "Performance Risk Refresh가 Session Refresh보다 빠릅니다."
        )
    if delay > policy.maximum_refresh_delay_minutes:
        errors.append(
            "Performance Risk Refresh 허용시간을 초과했습니다."
        )
    return (not errors, round(delay, 4), errors)


def empty_refresh_state() -> (
    PostRunPerformanceRiskState
):
    now = datetime.now().isoformat()
    return PostRunPerformanceRiskState(
        state_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        record_count=0,
        refreshed_count=0,
        records=(),
    )


def build_refresh_state(
    records: tuple[
        PostRunPerformanceRiskRecord,
        ...,
    ],
    state_id: str,
    created_at: str,
) -> PostRunPerformanceRiskState:
    return PostRunPerformanceRiskState(
        state_id=state_id,
        created_at=created_at,
        updated_at=datetime.now().isoformat(),
        record_count=len(records),
        refreshed_count=len(records),
        records=records,
    )


def validate_refresh_state(
    state: PostRunPerformanceRiskState,
) -> tuple[bool, list[str]]:
    if not isinstance(
        state,
        PostRunPerformanceRiskState,
    ):
        return (
            False,
            ["Performance Risk State 형식이 올바르지 않습니다."],
        )
    errors: list[str] = []
    if state.record_count != len(state.records):
        errors.append(
            "Refresh Record Count가 목록과 다릅니다."
        )
    if state.refreshed_count != len(state.records):
        errors.append(
            "Refreshed Count가 목록과 다릅니다."
        )
    if len(
        {
            record.session_refresh_id
            for record in state.records
        }
    ) != len(state.records):
        errors.append(
            "중복 Session Refresh ID가 있습니다."
        )
    return (not errors, errors)


def record_from_dict(
    payload: dict[str, Any],
) -> PostRunPerformanceRiskRecord:
    return PostRunPerformanceRiskRecord(
        **{
            **payload,
            "reasons": tuple(payload.get("reasons", [])),
            "warnings": tuple(
                payload.get("warnings", [])
            ),
        }
    )


def state_from_dict(
    payload: dict[str, Any],
) -> PostRunPerformanceRiskState:
    records = tuple(
        record_from_dict(item)
        for item in payload.get("records", [])
    )
    return build_refresh_state(
        records=records,
        state_id=payload["state_id"],
        created_at=payload["created_at"],
    )


def load_latest_refresh_state() -> (
    PostRunPerformanceRiskState
):
    path = (
        POST_RUN_PERFORMANCE_RISK_OUTPUT_DIRECTORY
        / "post_run_performance_risk_latest.json"
    )
    if not path.exists():
        return empty_refresh_state()
    payload = read_json_file(path)
    state_payload = payload.get("refresh_state")
    if not isinstance(state_payload, dict):
        raise ValueError(
            "Latest 파일에 Refresh State가 없습니다."
        )
    return state_from_dict(state_payload)


def run_post_run_performance_risk_refresh(
    session_refresh_result: PostRunSessionRefreshResult,
    refreshed_at: str | datetime,
    performance_builder: Callable[
        [Any],
        PaperPortfolioPerformanceResult,
    ],
    risk_builder: Callable[
        [PaperPortfolioPerformanceResult],
        PaperTradingRiskMonitorResult,
    ],
    refresh_state: (
        PostRunPerformanceRiskState
        | None
    ) = None,
    refresh_policy: (
        PostRunPerformanceRiskPolicy
        | None
    ) = None,
) -> PostRunPerformanceRiskResult:
    """
    갱신된 Session을 기준으로 Performance와 Risk를 재평가합니다.

    Builder의 구체적인 데이터 조회 방식은 다음 버전에서 연결하며,
    이 함수는 Broker API 또는 주문 기능을 직접 호출하지 않습니다.
    """

    policy = (
        refresh_policy
        if refresh_policy is not None
        else PostRunPerformanceRiskPolicy()
    )
    state = (
        refresh_state
        if refresh_state is not None
        else load_latest_refresh_state()
    )

    policy_valid, policy_errors = (
        validate_refresh_policy(policy)
    )
    session_valid, session_errors = (
        validate_session_refresh(
            session_refresh_result
        )
    )
    state_valid, state_errors = (
        validate_refresh_state(state)
    )

    parsed_refreshed_at: datetime | None = None
    timing_valid = False
    delay_minutes = 0.0
    timing_errors: list[str] = []
    try:
        parsed_refreshed_at = parse_datetime(
            refreshed_at,
            "Refreshed At",
        )
        (
            timing_valid,
            delay_minutes,
            timing_errors,
        ) = validate_refresh_timing(
            session_refresh_result,
            parsed_refreshed_at,
            policy,
        )
    except (TypeError, ValueError) as error:
        timing_errors.append(str(error))

    session_refresh_id = getattr(
        session_refresh_result,
        "refresh_id",
        None,
    )
    duplicate_detected = bool(
        session_refresh_id
        and session_refresh_id
        in {
            record.session_refresh_id
            for record in state.records
        }
    )
    duplicate_valid = not duplicate_detected

    performance_called = False
    risk_called = False
    performance: (
        PaperPortfolioPerformanceResult
        | None
    ) = None
    risk: PaperTradingRiskMonitorResult | None = None
    performance_valid = False
    risk_valid = False
    match_valid = False
    builder_errors: list[str] = []
    performance_errors: list[str] = []
    risk_errors: list[str] = []
    match_errors: list[str] = []

    preflight = bool(
        policy_valid
        and session_valid
        and state_valid
        and timing_valid
        and duplicate_valid
        and callable(performance_builder)
        and callable(risk_builder)
    )

    if preflight:
        try:
            performance_called = True
            performance = performance_builder(
                session_refresh_result.session_summary
            )
            (
                performance_valid,
                performance_errors,
            ) = validate_performance_result(
                performance
            )
        except Exception as error:
            builder_errors.append(
                f"Performance Builder 실행 실패: {error}"
            )

    if performance_valid:
        try:
            risk_called = True
            risk = risk_builder(performance)
            risk_valid, risk_errors = (
                validate_risk_result(risk)
            )
            if risk_valid:
                match_valid, match_errors = (
                    validate_source_match(
                        performance,
                        risk,
                    )
                )
        except Exception as error:
            builder_errors.append(
                f"Risk Builder 실행 실패: {error}"
            )

    if not policy_valid or not state_valid:
        status = "FAILED"
        status_label = (
            "Performance Risk Policy 또는 State 검사 실패"
        )
    elif duplicate_detected:
        status = "BLOCKED"
        status_label = (
            "중복 Performance Risk Refresh 차단"
        )
    elif not session_valid or not timing_valid:
        status = "BLOCKED"
        status_label = (
            "Session 또는 Refresh 시각 검사 차단"
        )
    elif not callable(
        performance_builder
    ) or not callable(risk_builder):
        status = "FAILED"
        status_label = "Refresh Builder가 없습니다"
    elif not (
        performance_valid
        and risk_valid
        and match_valid
    ):
        status = "FAILED"
        status_label = (
            "Performance 또는 Risk 결과 검사 실패"
        )
    else:
        status = "REFRESHED"
        status_label = (
            "Post-Run Performance와 Risk 갱신 완료"
        )

    warnings = [
        *policy_errors,
        *session_errors,
        *timing_errors,
        *state_errors,
        *performance_errors,
        *risk_errors,
        *match_errors,
        *builder_errors,
    ]
    if duplicate_detected:
        warnings.append(
            "동일 Session Refresh ID의 재평가를 차단했습니다."
        )

    reasons: list[str] = []
    record: PostRunPerformanceRiskRecord | None = None

    if status == "REFRESHED":
        reasons.append(
            "갱신된 Session을 기준으로 Performance와 Risk를 재평가했습니다."
        )
        record = PostRunPerformanceRiskRecord(
            refresh_id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(),
            session_refresh_id=(
                session_refresh_result.refresh_id
            ),
            integration_id=(
                session_refresh_result.integration_id
            ),
            ledger_id=session_refresh_result.ledger_id,
            session_summary_id=(
                session_refresh_result.session_summary_id
            ),
            session_status=(
                session_refresh_result
                .session_summary
                .session_status
            ),
            session_action=(
                session_refresh_result
                .session_summary
                .session_action
            ),
            performance_id=performance.performance_id,
            portfolio_id=performance.portfolio_id,
            performance_status=(
                performance.performance_status
            ),
            current_equity=performance.current_equity,
            cumulative_return_percent=(
                performance.cumulative_return_percent
            ),
            maximum_drawdown_percent=(
                performance.maximum_drawdown_percent
            ),
            risk_monitor_id=risk.monitor_id,
            risk_status=risk.risk_status,
            risk_action=risk.risk_action,
            refresh_delay_minutes=delay_minutes,
            performance_builder_called=(
                performance_called
            ),
            risk_builder_called=risk_called,
            session_checks_passed=session_valid,
            performance_checks_passed=(
                performance_valid
            ),
            risk_checks_passed=risk_valid,
            source_match_checks_passed=(
                match_valid
            ),
            timing_checks_passed=timing_valid,
            duplicate_checks_passed=(
                duplicate_valid
            ),
            all_checks_passed=True,
            execution_blocked=True,
            broker_api_called=False,
            broker_order_created=False,
            live_order_created=False,
            live_execution_authorized=False,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
        )
    elif status == "BLOCKED":
        reasons.append(
            "Session, 시간 또는 중복 검사로 재평가를 차단했습니다."
        )
    else:
        reasons.append(
            "Performance 또는 Risk Builder 결과 검사에 실패했습니다."
        )

    previous_record_count = state.record_count
    record_added = record is not None
    state_trimmed = False
    trimmed_record_count = 0

    if record is not None:
        records = (*state.records, record)
        if len(records) > policy.maximum_record_count:
            if policy.trim_oldest_records:
                trimmed_record_count = (
                    len(records)
                    - policy.maximum_record_count
                )
                records = records[
                    trimmed_record_count:
                ]
                state_trimmed = True
            else:
                warnings.append(
                    "Maximum Record Count를 초과했습니다."
                )
                records = state.records
                record = None
                record_added = False
        updated_state = build_refresh_state(
            records=tuple(records),
            state_id=state.state_id,
            created_at=state.created_at,
        )
    else:
        updated_state = state

    updated_state_valid, updated_errors = (
        validate_refresh_state(
            updated_state
        )
    )
    warnings.extend(updated_errors)

    all_checks_passed = bool(
        updated_state_valid
        and status in VALID_REFRESH_STATUSES
        and (
            record_added
            or duplicate_detected
            or status in {"BLOCKED", "FAILED"}
        )
    )

    warnings.extend(
        [
            "V11.4는 Post-Run 성과와 Risk 재평가 단계입니다.",
            "Broker API, 실제 주문 및 Live Execution은 호출하지 않습니다.",
        ]
    )
    next_actions = (
        [
            "갱신된 Risk Status와 Action을 확인합니다.",
            "다음 단계에서 전체 Post-Run 결과를 최종 정리합니다.",
        ]
        if status == "REFRESHED"
        else [
            "Warnings에서 재평가 실패 원인을 확인합니다.",
            "동일 Session Refresh를 자동 재실행하지 않습니다.",
        ]
    )

    result = PostRunPerformanceRiskResult(
        version="V11.4",
        created_at=datetime.now().isoformat(),
        result_id=str(uuid.uuid4()),
        state_id=updated_state.state_id,
        refresh_id=(
            record.refresh_id
            if record is not None
            else None
        ),
        session_refresh_id=session_refresh_id,
        refresh_status=status,
        refresh_status_label=status_label,
        performance_builder_called=(
            performance_called
        ),
        risk_builder_called=risk_called,
        performance_refreshed=(
            performance_valid
        ),
        risk_refreshed=(
            risk_valid and match_valid
        ),
        performance_id=(
            performance.performance_id
            if performance is not None
            else None
        ),
        risk_monitor_id=(
            risk.monitor_id
            if risk is not None
            else None
        ),
        risk_status=(
            risk.risk_status
            if risk is not None
            else None
        ),
        risk_action=(
            risk.risk_action
            if risk is not None
            else None
        ),
        duplicate_detected=duplicate_detected,
        record_added=record_added,
        state_trimmed=state_trimmed,
        trimmed_record_count=trimmed_record_count,
        previous_record_count=(
            previous_record_count
        ),
        current_record_count=(
            updated_state.record_count
        ),
        policy_checks_passed=policy_valid,
        session_checks_passed=session_valid,
        performance_checks_passed=(
            performance_valid
        ),
        risk_checks_passed=risk_valid,
        source_match_checks_passed=(
            match_valid
        ),
        timing_checks_passed=timing_valid,
        duplicate_checks_passed=(
            duplicate_valid
        ),
        state_checks_passed=(
            updated_state_valid
        ),
        all_checks_passed=all_checks_passed,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        refresh_policy=policy,
        performance_result=performance,
        risk_result=risk,
        refresh_record=record,
        refresh_state=updated_state,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )
    print_post_run_performance_risk_refresh(
        result
    )
    return result


def save_post_run_performance_risk_refresh(
    result: PostRunPerformanceRiskResult,
) -> tuple[Path, Path]:
    directory = (
        POST_RUN_PERFORMANCE_RISK_OUTPUT_DIRECTORY
    )
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"post_run_performance_risk_{timestamp}.json"
    )
    latest_path = directory / (
        "post_run_performance_risk_latest.json"
    )
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    return (report_path, latest_path)


def load_latest_post_run_performance_risk() -> (
    dict[str, Any]
):
    path = (
        POST_RUN_PERFORMANCE_RISK_OUTPUT_DIRECTORY
        / "post_run_performance_risk_latest.json"
    )
    return read_json_file(path)


def print_post_run_performance_risk_refresh(
    result: PostRunPerformanceRiskResult,
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("V11.4 POST-RUN PERFORMANCE & RISK REFRESH")
    print("=" * line_length)
    print(
        f"Refresh status                : "
        f"{result.refresh_status}"
    )
    print(
        f"Refresh status label          : "
        f"{result.refresh_status_label}"
    )
    print(
        f"Session Refresh ID            : "
        f"{result.session_refresh_id}"
    )
    print(
        f"Performance ID                : "
        f"{result.performance_id}"
    )
    print(
        f"Risk Monitor ID               : "
        f"{result.risk_monitor_id}"
    )
    print(
        f"Risk status                   : "
        f"{result.risk_status}"
    )
    print(
        f"Risk action                   : "
        f"{result.risk_action}"
    )
    print()
    print("VALIDATION")
    print("-" * line_length)
    print(
        f"Session checks passed         : "
        f"{result.session_checks_passed}"
    )
    print(
        f"Performance checks passed     : "
        f"{result.performance_checks_passed}"
    )
    print(
        f"Risk checks passed            : "
        f"{result.risk_checks_passed}"
    )
    print(
        f"Source match checks passed    : "
        f"{result.source_match_checks_passed}"
    )
    print(
        f"Timing checks passed          : "
        f"{result.timing_checks_passed}"
    )
    print(
        f"Duplicate checks passed       : "
        f"{result.duplicate_checks_passed}"
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
        "주의: V11.4는 성과와 Risk만 재평가하며 "
        "Broker 주문을 실행하지 않습니다."
    )
