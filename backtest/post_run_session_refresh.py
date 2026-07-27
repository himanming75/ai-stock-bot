import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from backtest.approved_paper_run_ledger_integration import (
    ApprovedRunLedgerIntegrationResult,
)
from backtest.paper_trading_run_ledger import (
    PaperTradingRunLedgerResult,
    PaperTradingRunLedgerState,
)
from backtest.paper_trading_session_summary import (
    PaperTradingSessionSummaryResult,
    run_paper_trading_session_summary,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

POST_RUN_SESSION_REFRESH_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "post_run_session_refresh"
)

VALID_REFRESH_STATUSES = {
    "REFRESHED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PostRunSessionRefreshPolicy:
    """
    V11.3 Post-Run Session Refresh 정책입니다.

    V11.2로 연결된 최신 Ledger를 사용해 V10.8 Session Summary를
    다시 계산합니다.
    """

    require_linked_integration: bool = True
    require_updated_ledger: bool = True
    require_matching_ledger: bool = True
    require_safe_summary: bool = True
    reject_duplicate_integration_refresh: bool = True

    maximum_refresh_delay_minutes: int = 15
    maximum_record_count: int = 10_000
    trim_oldest_records: bool = True

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PostRunSessionRefreshRecord:
    refresh_id: str
    created_at: str

    integration_id: str
    launch_id: str
    approval_id: str
    plan_id: str

    ledger_update_id: str
    ledger_id: str
    ledger_entry_id: str
    source_run_id: str

    previous_entry_count: int
    refreshed_entry_count: int

    session_summary_id: str
    session_status: str
    session_action: str
    total_run_count: int
    completed_run_count: int
    blocked_run_count: int
    failed_run_count: int

    refresh_delay_minutes: float
    summary_builder_called: bool

    integration_checks_passed: bool
    ledger_checks_passed: bool
    source_match_checks_passed: bool
    timing_checks_passed: bool
    summary_checks_passed: bool
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
class PostRunSessionRefreshState:
    refresh_state_id: str
    created_at: str
    updated_at: str

    record_count: int
    refreshed_count: int

    records: tuple[
        PostRunSessionRefreshRecord,
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
class PostRunSessionRefreshResult:
    version: str
    created_at: str

    refresh_result_id: str
    refresh_state_id: str
    refresh_id: str | None

    refresh_status: str
    refresh_status_label: str

    integration_id: str | None
    launch_id: str | None
    ledger_update_id: str | None
    ledger_id: str | None
    session_summary_id: str | None

    summary_builder_called: bool
    session_refreshed: bool
    duplicate_detected: bool
    record_added: bool
    state_trimmed: bool
    trimmed_record_count: int
    previous_record_count: int
    current_record_count: int

    policy_checks_passed: bool
    integration_checks_passed: bool
    ledger_checks_passed: bool
    source_match_checks_passed: bool
    timing_checks_passed: bool
    summary_checks_passed: bool
    duplicate_checks_passed: bool
    state_checks_passed: bool
    all_checks_passed: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    refresh_policy: PostRunSessionRefreshPolicy
    session_summary: (
        PaperTradingSessionSummaryResult
        | None
    )
    refresh_record: (
        PostRunSessionRefreshRecord
        | None
    )
    refresh_state: PostRunSessionRefreshState

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
        payload["session_summary"] = (
            self.session_summary.to_dict()
            if self.session_summary is not None
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
    policy: PostRunSessionRefreshPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        PostRunSessionRefreshPolicy,
    ):
        return (
            False,
            ["Refresh Policy 형식이 올바르지 않습니다."],
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
        "require_linked_integration": (
            policy.require_linked_integration
        ),
        "require_updated_ledger": (
            policy.require_updated_ledger
        ),
        "require_matching_ledger": (
            policy.require_matching_ledger
        ),
        "require_safe_summary": (
            policy.require_safe_summary
        ),
        "reject_duplicate_integration_refresh": (
            policy.reject_duplicate_integration_refresh
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }
    for name, value in required_true.items():
        if value is not True:
            errors.append(
                f"{name}는 V11.3에서 True여야 합니다."
            )

    if not isinstance(
        policy.trim_oldest_records,
        bool,
    ):
        errors.append(
            "trim_oldest_records가 bool 형식이 아닙니다."
        )

    return (not errors, errors)


def validate_integration_result(
    result: ApprovedRunLedgerIntegrationResult,
) -> tuple[bool, list[str]]:
    if not isinstance(
        result,
        ApprovedRunLedgerIntegrationResult,
    ):
        return (
            False,
            ["V11.2 Integration Result 형식이 아닙니다."],
        )

    errors: list[str] = []
    if result.version != "V11.2":
        errors.append(
            "Integration 버전이 V11.2가 아닙니다."
        )
    if result.integration_status != "LINKED":
        errors.append(
            "Integration Status가 LINKED가 아닙니다."
        )
    if not result.record_added:
        errors.append(
            "Integration Record가 추가되지 않았습니다."
        )
    if not result.all_checks_passed:
        errors.append(
            "Integration All Checks가 실패했습니다."
        )
    if result.integration_record is None:
        errors.append(
            "Integration Record가 없습니다."
        )
    if result.execution_blocked is not True:
        errors.append(
            "Integration Execution 차단 상태가 올바르지 않습니다."
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
            "Integration Result에 실거래 신호가 있습니다."
        )

    return (not errors, errors)


def validate_ledger_result(
    result: PaperTradingRunLedgerResult,
) -> tuple[bool, list[str]]:
    if not isinstance(
        result,
        PaperTradingRunLedgerResult,
    ):
        return (
            False,
            ["V10.7 Ledger Result 형식이 아닙니다."],
        )

    errors: list[str] = []
    if result.version != "V10.7":
        errors.append(
            "Ledger 버전이 V10.7이 아닙니다."
        )
    if result.ledger_status != "UPDATED":
        errors.append(
            "Ledger Status가 UPDATED가 아닙니다."
        )
    if not result.entry_added:
        errors.append(
            "Ledger Entry가 추가되지 않았습니다."
        )
    if not result.all_checks_passed:
        errors.append(
            "Ledger All Checks가 실패했습니다."
        )
    if not isinstance(
        result.ledger_state,
        PaperTradingRunLedgerState,
    ):
        errors.append(
            "Ledger State가 올바르지 않습니다."
        )
    if result.execution_blocked is not True:
        errors.append(
            "Ledger Execution 차단 상태가 올바르지 않습니다."
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
            "Ledger Result에 실거래 신호가 있습니다."
        )

    return (not errors, errors)


def validate_source_match(
    integration: ApprovedRunLedgerIntegrationResult,
    ledger: PaperTradingRunLedgerResult,
) -> tuple[bool, list[str]]:
    errors: list[str] = []

    if integration.ledger_update_id != (
        ledger.ledger_update_id
    ):
        errors.append(
            "Integration과 Ledger Update ID가 다릅니다."
        )
    if integration.ledger_id != ledger.ledger_id:
        errors.append(
            "Integration과 Ledger ID가 다릅니다."
        )
    if integration.source_run_id != (
        ledger.source_run_id
    ):
        errors.append(
            "Integration과 Ledger Source Run ID가 다릅니다."
        )
    if (
        integration.integration_record is not None
        and ledger.ledger_entry is not None
        and integration.integration_record.ledger_entry_id
        != ledger.ledger_entry.ledger_entry_id
    ):
        errors.append(
            "Integration과 Ledger Entry ID가 다릅니다."
        )

    return (not errors, errors)


def validate_refresh_timing(
    integration: ApprovedRunLedgerIntegrationResult,
    refreshed_at: datetime,
    policy: PostRunSessionRefreshPolicy,
) -> tuple[bool, float, list[str]]:
    try:
        integration_time = parse_datetime(
            integration.created_at,
            "Integration Created At",
        )
    except (TypeError, ValueError) as error:
        return (False, 0.0, [str(error)])

    if (
        integration_time.tzinfo is None
    ) != (
        refreshed_at.tzinfo is None
    ):
        return (
            False,
            0.0,
            ["Integration과 Refresh 시각의 Timezone 형식이 다릅니다."],
        )

    delay_minutes = (
        refreshed_at - integration_time
    ).total_seconds() / 60.0
    errors: list[str] = []

    if delay_minutes < 0:
        errors.append(
            "Refresh 시각이 Integration 생성 전입니다."
        )
    if (
        delay_minutes
        > policy.maximum_refresh_delay_minutes
    ):
        errors.append(
            "Session Refresh 허용시간을 초과했습니다."
        )

    return (
        not errors,
        round(delay_minutes, 4),
        errors,
    )


def validate_refreshed_summary(
    summary: PaperTradingSessionSummaryResult,
    ledger_state: PaperTradingRunLedgerState,
) -> tuple[bool, list[str]]:
    if not isinstance(
        summary,
        PaperTradingSessionSummaryResult,
    ):
        return (
            False,
            ["V10.8 Session Summary 형식이 아닙니다."],
        )

    errors: list[str] = []
    if summary.version != "V10.8":
        errors.append(
            "Session Summary 버전이 V10.8이 아닙니다."
        )
    if summary.source_ledger_id != (
        ledger_state.ledger_id
    ):
        errors.append(
            "Session Summary Source Ledger ID가 다릅니다."
        )
    if summary.total_run_count != (
        ledger_state.entry_count
    ):
        errors.append(
            "Session Summary Run Count가 Ledger와 다릅니다."
        )
    if not summary.all_checks_passed:
        errors.append(
            "Session Summary All Checks가 실패했습니다."
        )
    if summary.execution_blocked is not True:
        errors.append(
            "Session Summary Execution 차단 상태가 올바르지 않습니다."
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
            "Session Summary에 실거래 신호가 있습니다."
        )

    return (not errors, errors)


def empty_refresh_state() -> (
    PostRunSessionRefreshState
):
    now = datetime.now().isoformat()
    return PostRunSessionRefreshState(
        refresh_state_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        record_count=0,
        refreshed_count=0,
        records=(),
    )


def build_refresh_state(
    records: tuple[
        PostRunSessionRefreshRecord,
        ...,
    ],
    refresh_state_id: str,
    created_at: str,
) -> PostRunSessionRefreshState:
    return PostRunSessionRefreshState(
        refresh_state_id=refresh_state_id,
        created_at=created_at,
        updated_at=datetime.now().isoformat(),
        record_count=len(records),
        refreshed_count=len(records),
        records=records,
    )


def validate_refresh_state(
    state: PostRunSessionRefreshState,
) -> tuple[bool, list[str]]:
    if not isinstance(
        state,
        PostRunSessionRefreshState,
    ):
        return (
            False,
            ["Refresh State 형식이 올바르지 않습니다."],
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
            record.integration_id
            for record in state.records
        }
    ) != len(state.records):
        errors.append(
            "중복 Integration ID Refresh가 있습니다."
        )

    return (not errors, errors)


def refresh_record_from_dict(
    payload: dict[str, Any],
) -> PostRunSessionRefreshRecord:
    return PostRunSessionRefreshRecord(
        **{
            **payload,
            "reasons": tuple(payload.get("reasons", [])),
            "warnings": tuple(
                payload.get("warnings", [])
            ),
        }
    )


def refresh_state_from_dict(
    payload: dict[str, Any],
) -> PostRunSessionRefreshState:
    records = tuple(
        refresh_record_from_dict(item)
        for item in payload.get("records", [])
    )
    return build_refresh_state(
        records=records,
        refresh_state_id=payload[
            "refresh_state_id"
        ],
        created_at=payload["created_at"],
    )


def load_latest_refresh_state() -> (
    PostRunSessionRefreshState
):
    path = (
        POST_RUN_SESSION_REFRESH_OUTPUT_DIRECTORY
        / "post_run_session_refresh_latest.json"
    )
    if not path.exists():
        return empty_refresh_state()

    payload = read_json_file(path)
    state_payload = payload.get("refresh_state")
    if not isinstance(state_payload, dict):
        raise ValueError(
            "Latest 파일에 Refresh State가 없습니다."
        )
    return refresh_state_from_dict(
        state_payload
    )


def run_post_run_session_refresh(
    integration_result: ApprovedRunLedgerIntegrationResult,
    ledger_result: PaperTradingRunLedgerResult,
    refreshed_at: str | datetime,
    summary_builder: Callable[
        [PaperTradingRunLedgerState],
        PaperTradingSessionSummaryResult,
    ] = run_paper_trading_session_summary,
    refresh_state: (
        PostRunSessionRefreshState
        | None
    ) = None,
    refresh_policy: (
        PostRunSessionRefreshPolicy
        | None
    ) = None,
) -> PostRunSessionRefreshResult:
    """
    연결 완료된 최신 Ledger로 V10.8 Session Summary를 갱신합니다.

    실제 Broker API 또는 주문을 실행하지 않습니다.
    """

    policy = (
        refresh_policy
        if refresh_policy is not None
        else PostRunSessionRefreshPolicy()
    )
    state = (
        refresh_state
        if refresh_state is not None
        else load_latest_refresh_state()
    )

    policy_valid, policy_errors = (
        validate_refresh_policy(policy)
    )
    integration_valid, integration_errors = (
        validate_integration_result(
            integration_result
        )
    )
    ledger_valid, ledger_errors = (
        validate_ledger_result(
            ledger_result
        )
    )
    match_valid, match_errors = (
        validate_source_match(
            integration_result,
            ledger_result,
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
            integration_result,
            parsed_refreshed_at,
            policy,
        )
    except (TypeError, ValueError) as error:
        timing_errors.append(str(error))

    integration_id = getattr(
        integration_result,
        "integration_id",
        None,
    )
    duplicate_detected = bool(
        integration_id
        and integration_id
        in {
            record.integration_id
            for record in state.records
        }
    )
    duplicate_valid = not duplicate_detected

    summary_builder_called = False
    summary: (
        PaperTradingSessionSummaryResult
        | None
    ) = None
    summary_valid = False
    summary_errors: list[str] = []

    preflight_passed = bool(
        policy_valid
        and integration_valid
        and ledger_valid
        and match_valid
        and timing_valid
        and state_valid
        and duplicate_valid
        and callable(summary_builder)
    )

    if preflight_passed:
        try:
            summary_builder_called = True
            summary = summary_builder(
                ledger_result.ledger_state
            )
            summary_valid, summary_errors = (
                validate_refreshed_summary(
                    summary,
                    ledger_result.ledger_state,
                )
            )
        except Exception as error:
            summary_errors.append(
                f"Session Summary Builder 실행 실패: {error}"
            )

    if not policy_valid or not state_valid:
        status = "FAILED"
        status_label = (
            "Refresh Policy 또는 State 검사 실패"
        )
    elif duplicate_detected:
        status = "BLOCKED"
        status_label = "중복 Session Refresh 차단"
    elif not (
        integration_valid
        and ledger_valid
        and match_valid
        and timing_valid
    ):
        status = "BLOCKED"
        status_label = "Session Refresh 사전검사 차단"
    elif not callable(summary_builder):
        status = "FAILED"
        status_label = (
            "Session Summary Builder가 없습니다"
        )
    elif not summary_valid:
        status = "FAILED"
        status_label = (
            "갱신된 Session Summary 검사 실패"
        )
    else:
        status = "REFRESHED"
        status_label = (
            "Post-Run Session Summary 갱신 완료"
        )

    warnings = [
        *policy_errors,
        *integration_errors,
        *ledger_errors,
        *match_errors,
        *timing_errors,
        *state_errors,
        *summary_errors,
    ]
    if duplicate_detected:
        warnings.append(
            "동일 Integration ID의 Session Refresh를 차단했습니다."
        )

    reasons: list[str] = []
    record: PostRunSessionRefreshRecord | None = None

    if status == "REFRESHED":
        reasons.append(
            "연결된 최신 Ledger로 V10.8 Session Summary를 갱신했습니다."
        )
        integration_record = (
            integration_result.integration_record
        )
        record = PostRunSessionRefreshRecord(
            refresh_id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(),
            integration_id=(
                integration_result.integration_id
            ),
            launch_id=integration_result.launch_id,
            approval_id=(
                integration_result.approval_id
            ),
            plan_id=integration_result.plan_id,
            ledger_update_id=(
                ledger_result.ledger_update_id
            ),
            ledger_id=ledger_result.ledger_id,
            ledger_entry_id=(
                integration_record.ledger_entry_id
            ),
            source_run_id=(
                ledger_result.source_run_id
            ),
            previous_entry_count=(
                ledger_result.previous_entry_count
            ),
            refreshed_entry_count=(
                ledger_result.ledger_state.entry_count
            ),
            session_summary_id=(
                summary.session_summary_id
            ),
            session_status=summary.session_status,
            session_action=summary.session_action,
            total_run_count=summary.total_run_count,
            completed_run_count=(
                summary.completed_run_count
            ),
            blocked_run_count=(
                summary.blocked_run_count
            ),
            failed_run_count=(
                summary.failed_run_count
            ),
            refresh_delay_minutes=delay_minutes,
            summary_builder_called=(
                summary_builder_called
            ),
            integration_checks_passed=(
                integration_valid
            ),
            ledger_checks_passed=ledger_valid,
            source_match_checks_passed=(
                match_valid
            ),
            timing_checks_passed=timing_valid,
            summary_checks_passed=summary_valid,
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
            "Integration, Ledger, 시간 또는 중복 검사로 갱신을 차단했습니다."
        )
    else:
        reasons.append(
            "Summary Builder 또는 갱신 결과 검사에 실패했습니다."
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
                    "Maximum Refresh Record Count를 초과했습니다."
                )
                records = state.records
                record = None
                record_added = False

        updated_state = build_refresh_state(
            records=tuple(records),
            refresh_state_id=(
                state.refresh_state_id
            ),
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
            "V11.3은 Post-Run Session Summary 갱신 단계입니다.",
            "Broker API, 실제 주문 및 Live Execution은 호출하지 않습니다.",
        ]
    )

    next_actions = (
        [
            "갱신된 Session Status와 Action을 확인합니다.",
            "다음 단계에서 성과와 Risk 상태를 함께 재평가합니다.",
        ]
        if status == "REFRESHED"
        else [
            "Warnings에서 Refresh 실패 원인을 확인합니다.",
            "동일 Integration을 자동 재실행하지 않습니다.",
        ]
    )

    result = PostRunSessionRefreshResult(
        version="V11.3",
        created_at=datetime.now().isoformat(),
        refresh_result_id=str(uuid.uuid4()),
        refresh_state_id=(
            updated_state.refresh_state_id
        ),
        refresh_id=(
            record.refresh_id
            if record is not None
            else None
        ),
        refresh_status=status,
        refresh_status_label=status_label,
        integration_id=integration_id,
        launch_id=getattr(
            integration_result,
            "launch_id",
            None,
        ),
        ledger_update_id=getattr(
            ledger_result,
            "ledger_update_id",
            None,
        ),
        ledger_id=getattr(
            ledger_result,
            "ledger_id",
            None,
        ),
        session_summary_id=(
            summary.session_summary_id
            if summary is not None
            else None
        ),
        summary_builder_called=(
            summary_builder_called
        ),
        session_refreshed=(
            status == "REFRESHED"
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
        integration_checks_passed=(
            integration_valid
        ),
        ledger_checks_passed=ledger_valid,
        source_match_checks_passed=(
            match_valid
        ),
        timing_checks_passed=timing_valid,
        summary_checks_passed=summary_valid,
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
        session_summary=summary,
        refresh_record=record,
        refresh_state=updated_state,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_post_run_session_refresh(result)
    return result


def save_post_run_session_refresh(
    result: PostRunSessionRefreshResult,
) -> tuple[Path, Path]:
    directory = (
        POST_RUN_SESSION_REFRESH_OUTPUT_DIRECTORY
    )
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"post_run_session_refresh_{timestamp}.json"
    )
    latest_path = directory / (
        "post_run_session_refresh_latest.json"
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    return (report_path, latest_path)


def load_latest_post_run_session_refresh() -> (
    dict[str, Any]
):
    path = (
        POST_RUN_SESSION_REFRESH_OUTPUT_DIRECTORY
        / "post_run_session_refresh_latest.json"
    )
    return read_json_file(path)


def print_post_run_session_refresh(
    result: PostRunSessionRefreshResult,
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("V11.3 POST-RUN SESSION REFRESH")
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
        f"Integration ID                : "
        f"{result.integration_id}"
    )
    print(
        f"Ledger Update ID              : "
        f"{result.ledger_update_id}"
    )
    print(
        f"Session Summary ID            : "
        f"{result.session_summary_id}"
    )
    print(
        f"Summary builder called        : "
        f"{result.summary_builder_called}"
    )
    print(
        f"Session refreshed             : "
        f"{result.session_refreshed}"
    )
    print()
    print("VALIDATION")
    print("-" * line_length)
    print(
        f"Integration checks passed     : "
        f"{result.integration_checks_passed}"
    )
    print(
        f"Ledger checks passed          : "
        f"{result.ledger_checks_passed}"
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
        f"Summary checks passed         : "
        f"{result.summary_checks_passed}"
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
        "주의: V11.3은 Session Summary만 갱신하며 "
        "Broker 주문을 실행하지 않습니다."
    )
