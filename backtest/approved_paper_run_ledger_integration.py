import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.approved_paper_run_launcher import (
    ApprovedPaperRunLauncherResult,
)
from backtest.paper_trading_run_ledger import (
    PaperTradingRunLedgerResult,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

APPROVED_RUN_LEDGER_INTEGRATION_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "approved_run_ledger_integration"
)

VALID_INTEGRATION_STATUSES = {
    "LINKED",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class ApprovedRunLedgerIntegrationPolicy:
    """
    V11.2 Approved Run Ledger Integration 정책입니다.

    V11.1 수동 실행과 V10.7 Ledger 갱신을 하나의 감사 기록으로
    연결합니다. 기존 V10.7 데이터 구조는 변경하지 않습니다.
    """

    require_completed_launch: bool = True
    require_successful_ledger_update: bool = True
    require_matching_source_run: bool = True
    reject_duplicate_launch_id: bool = True

    maximum_link_delay_minutes: int = 10
    maximum_record_count: int = 10_000
    trim_oldest_records: bool = True

    require_execution_safety: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ApprovedRunLedgerIntegrationRecord:
    integration_id: str
    created_at: str

    launch_id: str
    approval_id: str
    plan_id: str

    launcher_result_id: str
    launcher_created_at: str
    launch_status: str

    ledger_update_id: str
    ledger_id: str
    ledger_created_at: str
    ledger_status: str
    ledger_entry_id: str
    source_run_id: str
    source_run_type: str
    source_run_status: str

    link_delay_minutes: float

    launch_checks_passed: bool
    ledger_checks_passed: bool
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
class ApprovedRunLedgerIntegrationState:
    integration_state_id: str
    created_at: str
    updated_at: str

    record_count: int
    linked_count: int

    records: tuple[
        ApprovedRunLedgerIntegrationRecord,
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
class ApprovedRunLedgerIntegrationResult:
    version: str
    created_at: str

    integration_result_id: str
    integration_state_id: str
    integration_id: str | None

    integration_status: str
    integration_status_label: str

    launch_id: str | None
    approval_id: str | None
    plan_id: str | None
    ledger_update_id: str | None
    ledger_entry_id: str | None
    source_run_id: str | None

    record_added: bool
    duplicate_detected: bool
    state_trimmed: bool
    trimmed_record_count: int
    previous_record_count: int
    current_record_count: int

    policy_checks_passed: bool
    launch_checks_passed: bool
    ledger_checks_passed: bool
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

    integration_policy: (
        ApprovedRunLedgerIntegrationPolicy
    )
    integration_record: (
        ApprovedRunLedgerIntegrationRecord
        | None
    )
    integration_state: (
        ApprovedRunLedgerIntegrationState
    )

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["integration_policy"] = (
            self.integration_policy.to_dict()
        )
        payload["integration_record"] = (
            self.integration_record.to_dict()
            if self.integration_record is not None
            else None
        )
        payload["integration_state"] = (
            self.integration_state.to_dict()
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


def validate_integration_policy(
    policy: ApprovedRunLedgerIntegrationPolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        ApprovedRunLedgerIntegrationPolicy,
    ):
        return (
            False,
            ["Integration Policy 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []

    integer_fields = {
        "maximum_link_delay_minutes": (
            policy.maximum_link_delay_minutes
        ),
        "maximum_record_count": (
            policy.maximum_record_count
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
        "require_completed_launch": (
            policy.require_completed_launch
        ),
        "require_successful_ledger_update": (
            policy.require_successful_ledger_update
        ),
        "require_matching_source_run": (
            policy.require_matching_source_run
        ),
        "reject_duplicate_launch_id": (
            policy.reject_duplicate_launch_id
        ),
        "require_execution_safety": (
            policy.require_execution_safety
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }
    for name, value in required_true.items():
        if value is not True:
            errors.append(
                f"{name}는 V11.2에서 True여야 합니다."
            )

    if not isinstance(
        policy.trim_oldest_records,
        bool,
    ):
        errors.append(
            "trim_oldest_records가 bool 형식이 아닙니다."
        )

    return (not errors, errors)


def validate_launch_result(
    result: ApprovedPaperRunLauncherResult,
) -> tuple[bool, list[str]]:
    if not isinstance(
        result,
        ApprovedPaperRunLauncherResult,
    ):
        return (
            False,
            ["V11.1 Launcher Result 형식이 아닙니다."],
        )

    errors: list[str] = []

    if result.version != "V11.1":
        errors.append(
            "Launcher Result 버전이 V11.1이 아닙니다."
        )
    if result.launch_status != "COMPLETED":
        errors.append(
            "Launch Status가 COMPLETED가 아닙니다."
        )
    if not result.paper_run_completed:
        errors.append(
            "Paper Run이 완료되지 않았습니다."
        )
    if not result.executor_called:
        errors.append(
            "Paper Executor가 호출되지 않았습니다."
        )
    if not result.executor_checks_passed:
        errors.append(
            "Paper Executor 검사가 실패했습니다."
        )
    if not result.all_checks_passed:
        errors.append(
            "Launcher All Checks가 실패했습니다."
        )
    if not result.launch_id:
        errors.append("Launch ID가 비어 있습니다.")
    if not result.approval_id:
        errors.append("Approval ID가 비어 있습니다.")
    if not result.plan_id:
        errors.append("Plan ID가 비어 있습니다.")
    if result.execution_blocked is not True:
        errors.append(
            "Launcher Execution 차단 상태가 올바르지 않습니다."
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
            "Launcher Result에 실거래 신호가 있습니다."
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
            "Ledger Result 버전이 V10.7이 아닙니다."
        )
    if result.ledger_status != "UPDATED":
        errors.append(
            "Ledger Status가 UPDATED가 아닙니다."
        )
    if not result.entry_added:
        errors.append(
            "Ledger Entry가 추가되지 않았습니다."
        )
    if result.duplicate_detected:
        errors.append(
            "Ledger Result가 중복 Run입니다."
        )
    if not result.all_checks_passed:
        errors.append(
            "Ledger All Checks가 실패했습니다."
        )
    if result.ledger_entry is None:
        errors.append(
            "Ledger Entry가 없습니다."
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

    if result.ledger_entry is not None:
        entry = result.ledger_entry
        if not entry.entry_checks_passed:
            errors.append(
                "Ledger Entry 검사가 실패했습니다."
            )
        if any(
            (
                entry.source_broker_api_called,
                entry.source_broker_order_created,
                entry.source_live_order_created,
                entry.source_live_execution_authorized,
            )
        ):
            errors.append(
                "Ledger Entry에 실거래 신호가 있습니다."
            )

    return (not errors, errors)


def extract_executor_source_run_id(
    launch_result: ApprovedPaperRunLauncherResult,
) -> str | None:
    executor_result = launch_result.executor_result

    if isinstance(executor_result, dict):
        for key in (
            "run_id",
            "source_run_id",
            "pipeline_run_id",
            "batch_run_id",
        ):
            value = executor_result.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    for name in (
        "run_id",
        "source_run_id",
        "pipeline_run_id",
        "batch_run_id",
    ):
        value = getattr(
            executor_result,
            name,
            None,
        )
        if isinstance(value, str) and value:
            return value

    return None


def validate_source_match(
    launch_result: ApprovedPaperRunLauncherResult,
    ledger_result: PaperTradingRunLedgerResult,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    executor_run_id = (
        extract_executor_source_run_id(
            launch_result
        )
    )

    if not executor_run_id:
        errors.append(
            "Launcher Executor Result에서 Run ID를 찾을 수 없습니다."
        )
    elif (
        ledger_result.source_run_id
        != executor_run_id
    ):
        errors.append(
            "Executor Run ID와 Ledger Source Run ID가 다릅니다."
        )

    if (
        ledger_result.ledger_entry is not None
        and ledger_result.ledger_entry.run_id
        != ledger_result.source_run_id
    ):
        errors.append(
            "Ledger Entry Run ID와 Result Source Run ID가 다릅니다."
        )

    return (not errors, errors)


def validate_link_timing(
    launch_result: ApprovedPaperRunLauncherResult,
    ledger_result: PaperTradingRunLedgerResult,
    policy: ApprovedRunLedgerIntegrationPolicy,
) -> tuple[bool, float, list[str]]:
    errors: list[str] = []

    try:
        launch_time = parse_datetime(
            launch_result.created_at,
            "Launcher Created At",
        )
        ledger_time = parse_datetime(
            ledger_result.created_at,
            "Ledger Created At",
        )
    except (TypeError, ValueError) as error:
        return (False, 0.0, [str(error)])

    if (
        launch_time.tzinfo is None
    ) != (
        ledger_time.tzinfo is None
    ):
        return (
            False,
            0.0,
            ["Launcher와 Ledger 시각의 Timezone 형식이 다릅니다."],
        )

    delay_minutes = (
        ledger_time - launch_time
    ).total_seconds() / 60.0

    if delay_minutes < 0:
        errors.append(
            "Ledger Result가 Launcher Result보다 먼저 생성되었습니다."
        )
    if (
        delay_minutes
        > policy.maximum_link_delay_minutes
    ):
        errors.append(
            "Launcher와 Ledger 연결 허용시간을 초과했습니다."
        )

    return (
        not errors,
        round(delay_minutes, 4),
        errors,
    )


def empty_integration_state() -> (
    ApprovedRunLedgerIntegrationState
):
    now = datetime.now().isoformat()
    return ApprovedRunLedgerIntegrationState(
        integration_state_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        record_count=0,
        linked_count=0,
        records=(),
    )


def build_integration_state(
    records: tuple[
        ApprovedRunLedgerIntegrationRecord,
        ...,
    ],
    integration_state_id: str,
    created_at: str,
) -> ApprovedRunLedgerIntegrationState:
    return ApprovedRunLedgerIntegrationState(
        integration_state_id=integration_state_id,
        created_at=created_at,
        updated_at=datetime.now().isoformat(),
        record_count=len(records),
        linked_count=len(records),
        records=records,
    )


def validate_integration_state(
    state: ApprovedRunLedgerIntegrationState,
) -> tuple[bool, list[str]]:
    if not isinstance(
        state,
        ApprovedRunLedgerIntegrationState,
    ):
        return (
            False,
            ["Integration State 형식이 올바르지 않습니다."],
        )

    errors: list[str] = []
    if state.record_count != len(state.records):
        errors.append(
            "Integration Record Count가 목록과 다릅니다."
        )
    if state.linked_count != len(state.records):
        errors.append(
            "Linked Count가 목록과 다릅니다."
        )
    if len(
        {
            record.launch_id
            for record in state.records
        }
    ) != len(state.records):
        errors.append(
            "중복 Launch ID가 있습니다."
        )
    if len(
        {
            record.ledger_entry_id
            for record in state.records
        }
    ) != len(state.records):
        errors.append(
            "중복 Ledger Entry ID가 있습니다."
        )

    return (not errors, errors)


def integration_record_from_dict(
    payload: dict[str, Any],
) -> ApprovedRunLedgerIntegrationRecord:
    return ApprovedRunLedgerIntegrationRecord(
        **{
            **payload,
            "reasons": tuple(payload.get("reasons", [])),
            "warnings": tuple(
                payload.get("warnings", [])
            ),
        }
    )


def integration_state_from_dict(
    payload: dict[str, Any],
) -> ApprovedRunLedgerIntegrationState:
    records = tuple(
        integration_record_from_dict(item)
        for item in payload.get("records", [])
    )
    return build_integration_state(
        records=records,
        integration_state_id=payload[
            "integration_state_id"
        ],
        created_at=payload["created_at"],
    )


def load_latest_integration_state() -> (
    ApprovedRunLedgerIntegrationState
):
    path = (
        APPROVED_RUN_LEDGER_INTEGRATION_OUTPUT_DIRECTORY
        / "approved_run_ledger_integration_latest.json"
    )
    if not path.exists():
        return empty_integration_state()

    payload = read_json_file(path)
    state_payload = payload.get(
        "integration_state"
    )
    if not isinstance(state_payload, dict):
        raise ValueError(
            "Latest 파일에 Integration State가 없습니다."
        )
    return integration_state_from_dict(
        state_payload
    )


def run_approved_paper_run_ledger_integration(
    launch_result: ApprovedPaperRunLauncherResult,
    ledger_result: PaperTradingRunLedgerResult,
    integration_state: (
        ApprovedRunLedgerIntegrationState
        | None
    ) = None,
    integration_policy: (
        ApprovedRunLedgerIntegrationPolicy
        | None
    ) = None,
) -> ApprovedRunLedgerIntegrationResult:
    """
    V11.1 Launch와 V10.7 Ledger Update를 감사 기록으로 연결합니다.

    Broker API, Paper Executor 또는 주문 기능을 직접 호출하지 않습니다.
    """

    policy = (
        integration_policy
        if integration_policy is not None
        else ApprovedRunLedgerIntegrationPolicy()
    )
    state = (
        integration_state
        if integration_state is not None
        else load_latest_integration_state()
    )

    policy_valid, policy_errors = (
        validate_integration_policy(policy)
    )
    launch_valid, launch_errors = (
        validate_launch_result(launch_result)
    )
    ledger_valid, ledger_errors = (
        validate_ledger_result(ledger_result)
    )
    match_valid, match_errors = (
        validate_source_match(
            launch_result,
            ledger_result,
        )
    )
    timing_valid, delay_minutes, timing_errors = (
        validate_link_timing(
            launch_result,
            ledger_result,
            policy,
        )
    )
    state_valid, state_errors = (
        validate_integration_state(state)
    )

    launch_id = getattr(
        launch_result,
        "launch_id",
        None,
    )
    duplicate_detected = bool(
        launch_id
        and launch_id
        in {
            record.launch_id
            for record in state.records
        }
    )
    duplicate_valid = not duplicate_detected

    warnings = [
        *policy_errors,
        *launch_errors,
        *ledger_errors,
        *match_errors,
        *timing_errors,
        *state_errors,
    ]
    if duplicate_detected:
        warnings.append(
            "동일 Launch ID의 Ledger Integration을 차단했습니다."
        )

    if not policy_valid or not state_valid:
        status = "FAILED"
        status_label = (
            "Integration Policy 또는 State 검사 실패"
        )
    elif duplicate_detected:
        status = "BLOCKED"
        status_label = "중복 Ledger Integration 차단"
    elif not (
        launch_valid
        and ledger_valid
        and match_valid
        and timing_valid
    ):
        status = "BLOCKED"
        status_label = "Launch와 Ledger 연결 안전검사 차단"
    else:
        status = "LINKED"
        status_label = (
            "Approved Paper Run과 Ledger 연결 완료"
        )

    reasons: list[str] = []
    record: (
        ApprovedRunLedgerIntegrationRecord
        | None
    ) = None

    if status == "LINKED":
        reasons.append(
            "V11.1 수동 실행과 V10.7 Ledger Entry를 연결했습니다."
        )
        entry = ledger_result.ledger_entry
        record = ApprovedRunLedgerIntegrationRecord(
            integration_id=str(uuid.uuid4()),
            created_at=datetime.now().isoformat(),
            launch_id=launch_result.launch_id,
            approval_id=launch_result.approval_id,
            plan_id=launch_result.plan_id,
            launcher_result_id=(
                launch_result.launcher_result_id
            ),
            launcher_created_at=(
                launch_result.created_at
            ),
            launch_status=(
                launch_result.launch_status
            ),
            ledger_update_id=(
                ledger_result.ledger_update_id
            ),
            ledger_id=ledger_result.ledger_id,
            ledger_created_at=(
                ledger_result.created_at
            ),
            ledger_status=(
                ledger_result.ledger_status
            ),
            ledger_entry_id=(
                entry.ledger_entry_id
            ),
            source_run_id=(
                ledger_result.source_run_id
            ),
            source_run_type=(
                ledger_result.source_run_type
            ),
            source_run_status=(
                ledger_result.source_run_status
            ),
            link_delay_minutes=delay_minutes,
            launch_checks_passed=launch_valid,
            ledger_checks_passed=ledger_valid,
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
            "Launch, Ledger, Run ID, 시간 또는 중복 검사로 연결을 차단했습니다."
        )
    else:
        reasons.append(
            "Integration Policy 또는 State 오류로 연결하지 못했습니다."
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

        updated_state = build_integration_state(
            records=tuple(records),
            integration_state_id=(
                state.integration_state_id
            ),
            created_at=state.created_at,
        )
    else:
        updated_state = state

    updated_state_valid, updated_errors = (
        validate_integration_state(
            updated_state
        )
    )
    warnings.extend(updated_errors)

    all_checks_passed = bool(
        updated_state_valid
        and status in VALID_INTEGRATION_STATUSES
        and (
            record_added
            or duplicate_detected
            or status == "FAILED"
            or status == "BLOCKED"
        )
    )

    warnings.extend(
        [
            "V11.2는 실행 결과와 Ledger 기록을 연결하는 감사 단계입니다.",
            "Broker API, 실제 주문 및 Live Execution은 호출하지 않습니다.",
        ]
    )

    next_actions = (
        [
            "V10.8 Session Summary를 새 Ledger 상태로 갱신합니다.",
            "갱신된 성과와 Risk 상태를 다시 검토합니다.",
        ]
        if status == "LINKED"
        else [
            "Warnings에서 연결 차단 원인을 확인합니다.",
            "중복 기록을 우회하거나 기존 기록을 삭제하지 않습니다.",
        ]
    )

    result = ApprovedRunLedgerIntegrationResult(
        version="V11.2",
        created_at=datetime.now().isoformat(),
        integration_result_id=str(uuid.uuid4()),
        integration_state_id=(
            updated_state.integration_state_id
        ),
        integration_id=(
            record.integration_id
            if record is not None
            else None
        ),
        integration_status=status,
        integration_status_label=status_label,
        launch_id=launch_id,
        approval_id=getattr(
            launch_result,
            "approval_id",
            None,
        ),
        plan_id=getattr(
            launch_result,
            "plan_id",
            None,
        ),
        ledger_update_id=getattr(
            ledger_result,
            "ledger_update_id",
            None,
        ),
        ledger_entry_id=(
            ledger_result.ledger_entry.ledger_entry_id
            if isinstance(
                ledger_result,
                PaperTradingRunLedgerResult,
            )
            and ledger_result.ledger_entry is not None
            else None
        ),
        source_run_id=getattr(
            ledger_result,
            "source_run_id",
            None,
        ),
        record_added=record_added,
        duplicate_detected=duplicate_detected,
        state_trimmed=state_trimmed,
        trimmed_record_count=trimmed_record_count,
        previous_record_count=(
            previous_record_count
        ),
        current_record_count=(
            updated_state.record_count
        ),
        policy_checks_passed=policy_valid,
        launch_checks_passed=launch_valid,
        ledger_checks_passed=ledger_valid,
        source_match_checks_passed=match_valid,
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
        integration_policy=policy,
        integration_record=record,
        integration_state=updated_state,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_approved_run_ledger_integration(
        result
    )
    return result


def save_approved_run_ledger_integration(
    result: ApprovedRunLedgerIntegrationResult,
) -> tuple[Path, Path]:
    directory = (
        APPROVED_RUN_LEDGER_INTEGRATION_OUTPUT_DIRECTORY
    )
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"approved_run_ledger_integration_{timestamp}.json"
    )
    latest_path = directory / (
        "approved_run_ledger_integration_latest.json"
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    return (report_path, latest_path)


def load_latest_approved_run_ledger_integration() -> (
    dict[str, Any]
):
    path = (
        APPROVED_RUN_LEDGER_INTEGRATION_OUTPUT_DIRECTORY
        / "approved_run_ledger_integration_latest.json"
    )
    return read_json_file(path)


def print_approved_run_ledger_integration(
    result: ApprovedRunLedgerIntegrationResult,
) -> None:
    line_length = 120
    print()
    print("=" * line_length)
    print("V11.2 APPROVED RUN LEDGER INTEGRATION")
    print("=" * line_length)
    print(
        f"Integration status            : "
        f"{result.integration_status}"
    )
    print(
        f"Integration status label      : "
        f"{result.integration_status_label}"
    )
    print(
        f"Launch ID                     : "
        f"{result.launch_id}"
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
        f"Ledger Update ID              : "
        f"{result.ledger_update_id}"
    )
    print(
        f"Ledger Entry ID               : "
        f"{result.ledger_entry_id}"
    )
    print(
        f"Record added                  : "
        f"{result.record_added}"
    )
    print()
    print("VALIDATION")
    print("-" * line_length)
    print(
        f"Launch checks passed          : "
        f"{result.launch_checks_passed}"
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
        "주의: V11.2는 Ledger 연결 기록만 생성하며 "
        "Broker 주문을 실행하지 않습니다."
    )
