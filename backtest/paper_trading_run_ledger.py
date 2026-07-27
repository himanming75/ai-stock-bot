import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_trading_risk_gated_batch import (
    PaperTradingRiskGatedBatchResult,
)
from backtest.paper_trading_risk_gated_pipeline import (
    PaperTradingRiskGatedPipelineResult,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_TRADING_RUN_LEDGER_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_trading_run_ledger"
)


VALID_LEDGER_STATUSES = {
    "INITIALIZED",
    "UPDATED",
    "NO_CHANGE",
    "FAILED",
}


VALID_RUN_TYPES = {
    "DAILY_GATED",
    "BATCH_GATED",
}


VALID_RUN_STATUSES = {
    "COMPLETED",
    "PARTIAL",
    "BLOCKED",
    "FAILED",
}


@dataclass(frozen=True)
class PaperTradingRunLedgerPolicy:
    """
    V10.7 Paper Trading Run Ledger 정책입니다.

    V10.5와 V10.6 실행 이력을 누적하고 중복 기록을 차단합니다.
    """

    reject_duplicate_run_id: bool = True
    retain_blocked_runs: bool = True
    retain_failed_runs: bool = True

    maximum_entry_count: int = 10_000
    trim_oldest_entries: bool = True

    require_source_checks: bool = True
    require_execution_safety: bool = True

    save_output: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperTradingRunLedgerEntry:
    """
    한 번의 V10.5 또는 V10.6 실행 기록입니다.
    """

    ledger_entry_id: str
    recorded_at: str

    run_type: str
    run_id: str
    source_version: str
    source_created_at: str

    run_status: str
    run_status_label: str

    risk_monitor_id: str | None
    risk_status: str
    risk_action: str
    gate_status: str
    gate_passed: bool

    requested_symbols: list[str]
    requested_symbol_count: int

    completed_symbol_count: int
    blocked_symbol_count: int
    failed_symbol_count: int
    skipped_symbol_count: int

    initial_equity: float
    final_equity: float
    equity_change: float
    equity_change_percent: float

    source_checks_passed: bool
    source_execution_blocked: bool
    source_broker_api_called: bool
    source_broker_order_created: bool
    source_live_order_created: bool
    source_live_execution_authorized: bool

    entry_checks_passed: bool

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
        payload["reasons"] = list(self.reasons)
        payload["warnings"] = list(
            self.warnings
        )
        return payload


@dataclass(frozen=True)
class PaperTradingRunLedgerState:
    """
    누적 Run Ledger의 현재 상태입니다.
    """

    ledger_id: str
    created_at: str
    updated_at: str

    entry_count: int
    daily_run_count: int
    batch_run_count: int

    completed_run_count: int
    partial_run_count: int
    blocked_run_count: int
    failed_run_count: int

    total_requested_symbol_count: int
    total_completed_symbol_count: int
    total_blocked_symbol_count: int
    total_failed_symbol_count: int
    total_skipped_symbol_count: int

    cumulative_equity_change: float

    entries: tuple[
        PaperTradingRunLedgerEntry,
        ...,
    ] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["entries"] = [
            entry.to_dict()
            for entry in self.entries
        ]
        return payload


@dataclass
class PaperTradingRunLedgerResult:
    """
    V10.7 Ledger 갱신 결과입니다.
    """

    version: str
    created_at: str

    ledger_update_id: str
    ledger_id: str

    ledger_status: str
    ledger_status_label: str

    source_run_type: str | None
    source_run_id: str | None
    source_run_status: str | None

    entry_added: bool
    duplicate_detected: bool
    ledger_trimmed: bool
    trimmed_entry_count: int

    previous_entry_count: int
    current_entry_count: int

    policy_checks_passed: bool
    source_checks_passed: bool
    duplicate_checks_passed: bool
    entry_checks_passed: bool
    ledger_checks_passed: bool
    all_checks_passed: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    ledger_policy: PaperTradingRunLedgerPolicy
    ledger_entry: (
        PaperTradingRunLedgerEntry
        | None
    )
    ledger_state: PaperTradingRunLedgerState

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ledger_policy"] = (
            self.ledger_policy.to_dict()
        )
        payload["ledger_entry"] = (
            self.ledger_entry.to_dict()
            if self.ledger_entry is not None
            else None
        )
        payload["ledger_state"] = (
            self.ledger_state.to_dict()
        )
        return payload


def round_money(value: float) -> float:
    return round(float(value), 2)


def round_percent(value: float) -> float:
    return round(float(value), 4)


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    임시 파일을 이용해 JSON을 안전하게 저장합니다.
    """

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
    """
    JSON 파일을 읽고 Dictionary인지 확인합니다.
    """

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


def validate_ledger_policy(
    policy: PaperTradingRunLedgerPolicy,
) -> tuple[bool, list[str]]:
    """
    V10.7 Ledger Policy를 검사합니다.
    """

    if not isinstance(
        policy,
        PaperTradingRunLedgerPolicy,
    ):
        return (
            False,
            [
                (
                    "Policy가 "
                    "PaperTradingRunLedgerPolicy "
                    "형식이 아닙니다."
                )
            ],
        )

    errors: list[str] = []

    boolean_fields = {
        "reject_duplicate_run_id": (
            policy.reject_duplicate_run_id
        ),
        "retain_blocked_runs": (
            policy.retain_blocked_runs
        ),
        "retain_failed_runs": (
            policy.retain_failed_runs
        ),
        "trim_oldest_entries": (
            policy.trim_oldest_entries
        ),
        "require_source_checks": (
            policy.require_source_checks
        ),
        "require_execution_safety": (
            policy.require_execution_safety
        ),
        "save_output": policy.save_output,
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

    if (
        not isinstance(
            policy.maximum_entry_count,
            int,
        )
        or policy.maximum_entry_count <= 0
    ):
        errors.append(
            "Maximum Entry Count는 0보다 큰 int여야 합니다."
        )

    if not policy.reject_duplicate_run_id:
        errors.append(
            "V10.7에서는 Duplicate Run ID 차단이 필수입니다."
        )

    if not policy.retain_blocked_runs:
        errors.append(
            "차단된 Run도 Audit 목적으로 보존해야 합니다."
        )

    if not policy.retain_failed_runs:
        errors.append(
            "실패한 Run도 Audit 목적으로 보존해야 합니다."
        )

    if not policy.require_execution_safety:
        errors.append(
            "V10.7에서는 Execution Safety 검사가 필수입니다."
        )

    if not policy.paper_only:
        errors.append(
            "V10.7에서는 Paper Only가 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V10.7에서는 Live Execution Disabled가 "
            "True여야 합니다."
        )

    return (not errors, errors)


def empty_ledger_state() -> (
    PaperTradingRunLedgerState
):
    """
    빈 Ledger State를 생성합니다.
    """

    now = datetime.now().isoformat()

    return PaperTradingRunLedgerState(
        ledger_id=str(uuid.uuid4()),
        created_at=now,
        updated_at=now,
        entry_count=0,
        daily_run_count=0,
        batch_run_count=0,
        completed_run_count=0,
        partial_run_count=0,
        blocked_run_count=0,
        failed_run_count=0,
        total_requested_symbol_count=0,
        total_completed_symbol_count=0,
        total_blocked_symbol_count=0,
        total_failed_symbol_count=0,
        total_skipped_symbol_count=0,
        cumulative_equity_change=0.0,
        entries=(),
    )


def ledger_entry_from_dict(
    payload: dict[str, Any],
) -> PaperTradingRunLedgerEntry:
    """
    Dictionary를 Ledger Entry로 복원합니다.
    """

    required_fields = {
        item.name
        for item in (
            PaperTradingRunLedgerEntry
            .__dataclass_fields__
            .values()
        )
    }

    missing_fields = (
        required_fields - set(payload)
    )

    if missing_fields:
        raise ValueError(
            (
                "Ledger Entry 필드가 누락되었습니다: "
                f"{sorted(missing_fields)}"
            )
        )

    values = {
        field_name: payload[field_name]
        for field_name in required_fields
    }

    values["requested_symbols"] = list(
        values["requested_symbols"]
    )
    values["reasons"] = tuple(
        values["reasons"]
    )
    values["warnings"] = tuple(
        values["warnings"]
    )

    return PaperTradingRunLedgerEntry(
        **values
    )


def ledger_state_from_dict(
    payload: dict[str, Any],
) -> PaperTradingRunLedgerState:
    """
    Dictionary를 Ledger State로 복원합니다.
    """

    if not isinstance(payload, dict):
        raise TypeError(
            "Ledger State Payload는 Dictionary여야 합니다."
        )

    entries_payload = payload.get(
        "entries",
        [],
    )

    if not isinstance(entries_payload, list):
        raise ValueError(
            "Ledger Entries가 List가 아닙니다."
        )

    entries = tuple(
        ledger_entry_from_dict(entry)
        for entry in entries_payload
    )

    return build_ledger_state(
        entries=entries,
        ledger_id=str(
            payload.get(
                "ledger_id",
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


def calculate_equity_change_percent(
    initial_equity: float,
    equity_change: float,
) -> float:
    """
    시작 Equity 대비 변화율을 계산합니다.
    """

    if initial_equity <= 0:
        return 0.0

    return round_percent(
        equity_change
        / initial_equity
        * 100.0
    )


def validate_source_safety(
    source: (
        PaperTradingRiskGatedPipelineResult
        | PaperTradingRiskGatedBatchResult
    ),
) -> tuple[bool, list[str]]:
    """
    V10.5 또는 V10.6 결과의 공통 안전 상태를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        source,
        (
            PaperTradingRiskGatedPipelineResult,
            PaperTradingRiskGatedBatchResult,
        ),
    ):
        return (
            False,
            [
                (
                    "Source가 V10.5 또는 V10.6 "
                    "Result 형식이 아닙니다."
                )
            ],
        )

    expected_version = (
        "V10.5"
        if isinstance(
            source,
            PaperTradingRiskGatedPipelineResult,
        )
        else "V10.6"
    )

    if source.version != expected_version:
        errors.append(
            f"Source 버전이 {expected_version}이 아닙니다."
        )

    if source.execution_blocked is not True:
        errors.append(
            "Source Execution이 차단되지 않았습니다."
        )

    unsafe_flags = {
        "broker_api_called": source.broker_api_called,
        "broker_order_created": (
            source.broker_order_created
        ),
        "live_order_created": (
            source.live_order_created
        ),
        "live_execution_authorized": (
            source.live_execution_authorized
        ),
    }

    for field_name, value in unsafe_flags.items():
        if value is not False:
            errors.append(
                f"Source의 {field_name}가 False가 아닙니다."
            )

    return (not errors, errors)


def create_daily_ledger_entry(
    source: PaperTradingRiskGatedPipelineResult,
) -> PaperTradingRunLedgerEntry:
    """
    V10.5 Result를 Daily Ledger Entry로 변환합니다.
    """

    final_equity = (
        source.daily_pipeline_result.final_equity
        if source.daily_pipeline_result is not None
        else 0.0
    )
    initial_equity = (
        source.daily_pipeline_result.initial_cash
        if source.daily_pipeline_result is not None
        else 0.0
    )
    equity_change = round_money(
        final_equity - initial_equity
    )

    run_status = (
        source.gated_pipeline_status
    )

    entry_checks_passed = bool(
        run_status in VALID_RUN_STATUSES
        and source.execution_blocked
        and not source.broker_api_called
        and not source.broker_order_created
        and not source.live_order_created
        and not source.live_execution_authorized
    )

    completed_count = (
        1
        if run_status == "COMPLETED"
        else 0
    )
    blocked_count = (
        1
        if run_status == "BLOCKED"
        else 0
    )
    failed_count = (
        1
        if run_status == "FAILED"
        else 0
    )
    skipped_count = (
        1
        if source.daily_pipeline_skipped
        else 0
    )

    return PaperTradingRunLedgerEntry(
        ledger_entry_id=str(uuid.uuid4()),
        recorded_at=datetime.now().isoformat(),
        run_type="DAILY_GATED",
        run_id=source.gated_pipeline_id,
        source_version=source.version,
        source_created_at=source.created_at,
        run_status=run_status,
        run_status_label=(
            source.gated_pipeline_status_label
        ),
        risk_monitor_id=(
            source.risk_monitor_id
        ),
        risk_status=(
            source
            .risk_gate_decision
            .risk_status
        ),
        risk_action=(
            source
            .risk_gate_decision
            .risk_action
        ),
        gate_status=(
            source
            .risk_gate_decision
            .gate_status
        ),
        gate_passed=(
            source
            .risk_gate_decision
            .gate_passed
        ),
        requested_symbols=[
            source.symbol
        ],
        requested_symbol_count=1,
        completed_symbol_count=(
            completed_count
        ),
        blocked_symbol_count=blocked_count,
        failed_symbol_count=failed_count,
        skipped_symbol_count=skipped_count,
        initial_equity=round_money(
            initial_equity
        ),
        final_equity=round_money(
            final_equity
        ),
        equity_change=equity_change,
        equity_change_percent=(
            calculate_equity_change_percent(
                initial_equity,
                equity_change,
            )
        ),
        source_checks_passed=(
            source.all_checks_passed
        ),
        source_execution_blocked=(
            source.execution_blocked
        ),
        source_broker_api_called=(
            source.broker_api_called
        ),
        source_broker_order_created=(
            source.broker_order_created
        ),
        source_live_order_created=(
            source.live_order_created
        ),
        source_live_execution_authorized=(
            source.live_execution_authorized
        ),
        entry_checks_passed=(
            entry_checks_passed
        ),
        reasons=tuple(source.reasons),
        warnings=tuple(source.warnings),
    )


def create_batch_ledger_entry(
    source: PaperTradingRiskGatedBatchResult,
) -> PaperTradingRunLedgerEntry:
    """
    V10.6 Result를 Batch Ledger Entry로 변환합니다.
    """

    initial_equity = (
        source.batch_result.initial_cash
        if source.batch_result is not None
        else 0.0
    )
    final_equity = (
        source.batch_result.final_equity
        if source.batch_result is not None
        else 0.0
    )
    equity_change = round_money(
        final_equity - initial_equity
    )

    entry_checks_passed = bool(
        source.gated_batch_status
        in VALID_RUN_STATUSES
        and source.execution_blocked
        and not source.broker_api_called
        and not source.broker_order_created
        and not source.live_order_created
        and not source.live_execution_authorized
    )

    return PaperTradingRunLedgerEntry(
        ledger_entry_id=str(uuid.uuid4()),
        recorded_at=datetime.now().isoformat(),
        run_type="BATCH_GATED",
        run_id=source.gated_batch_id,
        source_version=source.version,
        source_created_at=source.created_at,
        run_status=source.gated_batch_status,
        run_status_label=(
            source.gated_batch_status_label
        ),
        risk_monitor_id=(
            source.risk_monitor_id
        ),
        risk_status=(
            source
            .risk_gate_decision
            .risk_status
        ),
        risk_action=(
            source
            .risk_gate_decision
            .risk_action
        ),
        gate_status=(
            source
            .risk_gate_decision
            .gate_status
        ),
        gate_passed=(
            source
            .risk_gate_decision
            .gate_passed
        ),
        requested_symbols=list(
            source.requested_symbols
        ),
        requested_symbol_count=(
            source.requested_symbol_count
        ),
        completed_symbol_count=(
            source.completed_symbol_count
        ),
        blocked_symbol_count=(
            source.blocked_symbol_count
        ),
        failed_symbol_count=(
            source.failed_symbol_count
        ),
        skipped_symbol_count=(
            source.skipped_symbol_count
        ),
        initial_equity=round_money(
            initial_equity
        ),
        final_equity=round_money(
            final_equity
        ),
        equity_change=equity_change,
        equity_change_percent=(
            calculate_equity_change_percent(
                initial_equity,
                equity_change,
            )
        ),
        source_checks_passed=(
            source.all_checks_passed
        ),
        source_execution_blocked=(
            source.execution_blocked
        ),
        source_broker_api_called=(
            source.broker_api_called
        ),
        source_broker_order_created=(
            source.broker_order_created
        ),
        source_live_order_created=(
            source.live_order_created
        ),
        source_live_execution_authorized=(
            source.live_execution_authorized
        ),
        entry_checks_passed=(
            entry_checks_passed
        ),
        reasons=tuple(source.reasons),
        warnings=tuple(source.warnings),
    )


def create_ledger_entry(
    source: (
        PaperTradingRiskGatedPipelineResult
        | PaperTradingRiskGatedBatchResult
    ),
) -> PaperTradingRunLedgerEntry:
    """
    Source 유형에 맞는 Ledger Entry를 생성합니다.
    """

    if isinstance(
        source,
        PaperTradingRiskGatedPipelineResult,
    ):
        return create_daily_ledger_entry(
            source
        )

    if isinstance(
        source,
        PaperTradingRiskGatedBatchResult,
    ):
        return create_batch_ledger_entry(
            source
        )

    raise TypeError(
        "지원하지 않는 Ledger Source입니다."
    )


def build_ledger_state(
    entries: tuple[
        PaperTradingRunLedgerEntry,
        ...,
    ],
    ledger_id: str | None = None,
    created_at: str | None = None,
) -> PaperTradingRunLedgerState:
    """
    Entry 목록으로 Ledger 집계 상태를 다시 계산합니다.
    """

    entry_count = len(entries)

    return PaperTradingRunLedgerState(
        ledger_id=(
            ledger_id
            or str(uuid.uuid4())
        ),
        created_at=(
            created_at
            or datetime.now().isoformat()
        ),
        updated_at=datetime.now().isoformat(),
        entry_count=entry_count,
        daily_run_count=sum(
            entry.run_type == "DAILY_GATED"
            for entry in entries
        ),
        batch_run_count=sum(
            entry.run_type == "BATCH_GATED"
            for entry in entries
        ),
        completed_run_count=sum(
            entry.run_status == "COMPLETED"
            for entry in entries
        ),
        partial_run_count=sum(
            entry.run_status == "PARTIAL"
            for entry in entries
        ),
        blocked_run_count=sum(
            entry.run_status == "BLOCKED"
            for entry in entries
        ),
        failed_run_count=sum(
            entry.run_status == "FAILED"
            for entry in entries
        ),
        total_requested_symbol_count=sum(
            entry.requested_symbol_count
            for entry in entries
        ),
        total_completed_symbol_count=sum(
            entry.completed_symbol_count
            for entry in entries
        ),
        total_blocked_symbol_count=sum(
            entry.blocked_symbol_count
            for entry in entries
        ),
        total_failed_symbol_count=sum(
            entry.failed_symbol_count
            for entry in entries
        ),
        total_skipped_symbol_count=sum(
            entry.skipped_symbol_count
            for entry in entries
        ),
        cumulative_equity_change=round_money(
            sum(
                entry.equity_change
                for entry in entries
            )
        ),
        entries=entries,
    )


def validate_ledger_state(
    state: PaperTradingRunLedgerState,
) -> tuple[bool, list[str]]:
    """
    Ledger 집계값과 Entry 목록이 일치하는지 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        state,
        PaperTradingRunLedgerState,
    ):
        return (
            False,
            [
                (
                    "Ledger State가 "
                    "PaperTradingRunLedgerState "
                    "형식이 아닙니다."
                )
            ],
        )

    rebuilt = build_ledger_state(
        entries=state.entries,
        ledger_id=state.ledger_id,
        created_at=state.created_at,
    )

    comparable_fields = (
        "entry_count",
        "daily_run_count",
        "batch_run_count",
        "completed_run_count",
        "partial_run_count",
        "blocked_run_count",
        "failed_run_count",
        "total_requested_symbol_count",
        "total_completed_symbol_count",
        "total_blocked_symbol_count",
        "total_failed_symbol_count",
        "total_skipped_symbol_count",
        "cumulative_equity_change",
    )

    for field_name in comparable_fields:
        if (
            getattr(state, field_name)
            != getattr(rebuilt, field_name)
        ):
            errors.append(
                f"Ledger 집계값 {field_name}가 Entry 목록과 다릅니다."
            )

    run_ids = [
        entry.run_id
        for entry in state.entries
    ]

    if len(run_ids) != len(set(run_ids)):
        errors.append(
            "Ledger에 중복 Run ID가 있습니다."
        )

    for entry in state.entries:
        if entry.run_type not in VALID_RUN_TYPES:
            errors.append(
                f"허용되지 않은 Run Type입니다: {entry.run_type}"
            )

        if entry.run_status not in VALID_RUN_STATUSES:
            errors.append(
                f"허용되지 않은 Run Status입니다: {entry.run_status}"
            )

        if not entry.run_id:
            errors.append(
                "Ledger Entry Run ID가 비어 있습니다."
            )

        if not entry.source_execution_blocked:
            errors.append(
                f"{entry.run_id}: Source Execution이 차단되지 않았습니다."
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
                f"{entry.run_id}: 실거래 안전 상태가 올바르지 않습니다."
            )

    return (not errors, errors)


def load_latest_ledger_state(
    default_state: (
        PaperTradingRunLedgerState
        | None
    ) = None,
) -> PaperTradingRunLedgerState:
    """
    최신 Ledger State를 읽습니다.
    파일이 없으면 빈 State를 반환합니다.
    """

    latest_path = (
        PAPER_TRADING_RUN_LEDGER_OUTPUT_DIRECTORY
        / "paper_trading_run_ledger_latest.json"
    )

    if not latest_path.exists():
        return (
            default_state
            if default_state is not None
            else empty_ledger_state()
        )

    payload = read_json_file(
        latest_path
    )

    state_payload = payload.get(
        "ledger_state",
        payload,
    )

    return ledger_state_from_dict(
        state_payload
    )


def run_paper_trading_run_ledger(
    source_result: (
        PaperTradingRiskGatedPipelineResult
        | PaperTradingRiskGatedBatchResult
    ),
    ledger_state: (
        PaperTradingRunLedgerState
        | None
    ) = None,
    ledger_policy: (
        PaperTradingRunLedgerPolicy
        | None
    ) = None,
) -> PaperTradingRunLedgerResult:
    """
    V10.5 또는 V10.6 결과 한 건을 Ledger에 추가합니다.

    실제 Broker API 또는 주문은 수행하지 않습니다.
    """

    policy = (
        ledger_policy
        if ledger_policy is not None
        else PaperTradingRunLedgerPolicy()
    )

    policy_valid, policy_errors = (
        validate_ledger_policy(policy)
    )

    working_state = (
        ledger_state
        if ledger_state is not None
        else load_latest_ledger_state()
    )

    previous_entry_count = (
        working_state.entry_count
    )

    source_valid, source_errors = (
        validate_source_safety(
            source_result
        )
    )

    state_valid, state_errors = (
        validate_ledger_state(
            working_state
        )
    )

    reasons: list[str] = []
    warnings: list[str] = []
    warnings.extend(policy_errors)
    warnings.extend(source_errors)
    warnings.extend(state_errors)

    ledger_entry: (
        PaperTradingRunLedgerEntry
        | None
    ) = None
    entry_added = False
    duplicate_detected = False
    ledger_trimmed = False
    trimmed_entry_count = 0

    source_run_id: str | None = None
    source_run_type: str | None = None
    source_run_status: str | None = None

    try:
        ledger_entry = create_ledger_entry(
            source_result
        )
        source_run_id = ledger_entry.run_id
        source_run_type = (
            ledger_entry.run_type
        )
        source_run_status = (
            ledger_entry.run_status
        )
    except Exception as error:
        warnings.append(
            f"Ledger Entry 생성 실패: {error}"
        )

    existing_run_ids = {
        entry.run_id
        for entry in working_state.entries
    }

    if (
        ledger_entry is not None
        and ledger_entry.run_id
        in existing_run_ids
    ):
        duplicate_detected = True

    duplicate_checks_passed = (
        not duplicate_detected
    )

    if (
        policy_valid
        and source_valid
        and state_valid
        and ledger_entry is not None
        and ledger_entry.entry_checks_passed
        and not duplicate_detected
    ):
        updated_entries = (
            *working_state.entries,
            ledger_entry,
        )

        if (
            len(updated_entries)
            > policy.maximum_entry_count
        ):
            if policy.trim_oldest_entries:
                trimmed_entry_count = (
                    len(updated_entries)
                    - policy.maximum_entry_count
                )
                updated_entries = (
                    updated_entries[
                        trimmed_entry_count:
                    ]
                )
                ledger_trimmed = True
            else:
                warnings.append(
                    "Maximum Entry Count를 초과했습니다."
                )

        if (
            len(updated_entries)
            <= policy.maximum_entry_count
        ):
            updated_state = build_ledger_state(
                entries=tuple(
                    updated_entries
                ),
                ledger_id=(
                    working_state.ledger_id
                ),
                created_at=(
                    working_state.created_at
                ),
            )
            entry_added = True
        else:
            updated_state = working_state
    else:
        updated_state = working_state

    updated_state_valid, updated_state_errors = (
        validate_ledger_state(
            updated_state
        )
    )
    warnings.extend(updated_state_errors)

    if not policy_valid:
        ledger_status = "FAILED"
        ledger_status_label = (
            "Ledger Policy 검사 실패"
        )
    elif not source_valid:
        ledger_status = "FAILED"
        ledger_status_label = (
            "Source 안전 검사 실패"
        )
    elif not state_valid:
        ledger_status = "FAILED"
        ledger_status_label = (
            "기존 Ledger State 검사 실패"
        )
    elif duplicate_detected:
        ledger_status = "NO_CHANGE"
        ledger_status_label = (
            "중복 Run ID로 기록하지 않음"
        )
    elif entry_added and previous_entry_count == 0:
        ledger_status = "INITIALIZED"
        ledger_status_label = (
            "첫 번째 Run Ledger 기록 완료"
        )
    elif entry_added:
        ledger_status = "UPDATED"
        ledger_status_label = (
            "Run Ledger 누적 기록 완료"
        )
    else:
        ledger_status = "FAILED"
        ledger_status_label = (
            "Run Ledger 기록 실패"
        )

    entry_checks_passed = bool(
        ledger_entry is not None
        and ledger_entry.entry_checks_passed
    )

    all_checks_passed = bool(
        policy_valid
        and source_valid
        and state_valid
        and updated_state_valid
        and entry_checks_passed
        and ledger_status
        in {
            "INITIALIZED",
            "UPDATED",
            "NO_CHANGE",
        }
        and (
            entry_added
            or duplicate_detected
        )
    )

    if ledger_status == "INITIALIZED":
        reasons.append(
            "새 Paper Trading Run Ledger를 생성했습니다."
        )
    elif ledger_status == "UPDATED":
        reasons.append(
            "새 실행 결과를 Run Ledger에 추가했습니다."
        )
    elif ledger_status == "NO_CHANGE":
        reasons.append(
            "동일한 Run ID가 이미 있어 중복 기록을 차단했습니다."
        )
    else:
        reasons.append(
            "검사 실패로 Run Ledger를 변경하지 않았습니다."
        )

    warnings.extend(
        [
            (
                "V10.7 Ledger는 연구용 Paper Trading "
                "실행 이력입니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 "
                "Live Execution은 모두 차단됩니다."
            ),
        ]
    )

    if ledger_status in {
        "INITIALIZED",
        "UPDATED",
    }:
        next_actions = [
            "Ledger의 Run Status와 Risk Action을 확인합니다.",
            "다음 V10.5 또는 V10.6 실행 결과를 계속 누적합니다.",
        ]
    elif ledger_status == "NO_CHANGE":
        next_actions = [
            "중복 Run ID가 의도된 재처리인지 확인합니다.",
            "새로운 실행 결과만 Ledger에 추가합니다.",
        ]
    else:
        next_actions = [
            "Warnings와 Source 안전 상태를 확인합니다.",
            "문제를 수정한 뒤 V10.7 Ledger를 다시 실행합니다.",
        ]

    result = PaperTradingRunLedgerResult(
        version="V10.7",
        created_at=datetime.now().isoformat(),
        ledger_update_id=str(uuid.uuid4()),
        ledger_id=updated_state.ledger_id,
        ledger_status=ledger_status,
        ledger_status_label=(
            ledger_status_label
        ),
        source_run_type=source_run_type,
        source_run_id=source_run_id,
        source_run_status=source_run_status,
        entry_added=entry_added,
        duplicate_detected=(
            duplicate_detected
        ),
        ledger_trimmed=ledger_trimmed,
        trimmed_entry_count=(
            trimmed_entry_count
        ),
        previous_entry_count=(
            previous_entry_count
        ),
        current_entry_count=(
            updated_state.entry_count
        ),
        policy_checks_passed=(
            policy_valid
        ),
        source_checks_passed=(
            source_valid
        ),
        duplicate_checks_passed=(
            duplicate_checks_passed
        ),
        entry_checks_passed=(
            entry_checks_passed
        ),
        ledger_checks_passed=(
            updated_state_valid
        ),
        all_checks_passed=(
            all_checks_passed
        ),
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        ledger_policy=policy,
        ledger_entry=ledger_entry,
        ledger_state=updated_state,
        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_trading_run_ledger(
        result
    )

    return result


def save_paper_trading_run_ledger(
    result: PaperTradingRunLedgerResult,
) -> tuple[Path, Path]:
    """
    V10.7 Report와 Latest Ledger JSON을 저장합니다.
    """

    PAPER_TRADING_RUN_LEDGER_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    report_path = (
        PAPER_TRADING_RUN_LEDGER_OUTPUT_DIRECTORY
        / (
            "paper_trading_run_ledger_"
            f"{timestamp}.json"
        )
    )
    latest_path = (
        PAPER_TRADING_RUN_LEDGER_OUTPUT_DIRECTORY
        / "paper_trading_run_ledger_latest.json"
    )

    result.report_path = str(report_path)
    result.latest_path = str(latest_path)

    payload = result.to_dict()

    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)

    return (report_path, latest_path)


def load_latest_paper_trading_run_ledger() -> (
    dict[str, Any]
):
    """
    최신 V10.7 전체 결과 JSON을 읽습니다.
    """

    latest_path = (
        PAPER_TRADING_RUN_LEDGER_OUTPUT_DIRECTORY
        / "paper_trading_run_ledger_latest.json"
    )

    return read_json_file(latest_path)


def print_paper_trading_run_ledger(
    result: PaperTradingRunLedgerResult,
) -> None:
    """
    V10.7 Ledger 결과를 터미널에 출력합니다.
    """

    line_length = 140
    state = result.ledger_state

    print()
    print("=" * line_length)
    print(
        "V10.7 PAPER TRADING RUN LEDGER"
    )
    print("=" * line_length)

    print(
        f"Ledger status                  : "
        f"{result.ledger_status}"
    )
    print(
        f"Ledger status label            : "
        f"{result.ledger_status_label}"
    )
    print(
        f"Ledger update ID               : "
        f"{result.ledger_update_id}"
    )
    print(
        f"Ledger ID                      : "
        f"{result.ledger_id}"
    )

    print()
    print("SOURCE RUN")
    print("-" * line_length)

    print(
        f"Source run type                : "
        f"{result.source_run_type}"
    )
    print(
        f"Source run ID                  : "
        f"{result.source_run_id}"
    )
    print(
        f"Source run status              : "
        f"{result.source_run_status}"
    )
    print(
        f"Entry added                    : "
        f"{result.entry_added}"
    )
    print(
        f"Duplicate detected             : "
        f"{result.duplicate_detected}"
    )
    print(
        f"Ledger trimmed                 : "
        f"{result.ledger_trimmed}"
    )

    print()
    print("LEDGER SUMMARY")
    print("-" * line_length)

    print(
        f"Entry count                    : "
        f"{state.entry_count}"
    )
    print(
        f"Daily runs                     : "
        f"{state.daily_run_count}"
    )
    print(
        f"Batch runs                     : "
        f"{state.batch_run_count}"
    )
    print(
        f"Completed runs                 : "
        f"{state.completed_run_count}"
    )
    print(
        f"Partial runs                   : "
        f"{state.partial_run_count}"
    )
    print(
        f"Blocked runs                   : "
        f"{state.blocked_run_count}"
    )
    print(
        f"Failed runs                    : "
        f"{state.failed_run_count}"
    )
    print(
        f"Requested symbols              : "
        f"{state.total_requested_symbol_count}"
    )
    print(
        f"Completed symbols              : "
        f"{state.total_completed_symbol_count}"
    )
    print(
        f"Skipped symbols                : "
        f"{state.total_skipped_symbol_count}"
    )
    print(
        f"Cumulative equity change       : "
        f"${state.cumulative_equity_change:,.2f}"
    )

    print()
    print("VALIDATION")
    print("-" * line_length)

    print(
        f"Policy checks passed           : "
        f"{result.policy_checks_passed}"
    )
    print(
        f"Source checks passed           : "
        f"{result.source_checks_passed}"
    )
    print(
        f"Duplicate checks passed        : "
        f"{result.duplicate_checks_passed}"
    )
    print(
        f"Entry checks passed            : "
        f"{result.entry_checks_passed}"
    )
    print(
        f"Ledger checks passed           : "
        f"{result.ledger_checks_passed}"
    )
    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * line_length)

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
        "주의: V10.7은 연구용 Paper Trading 실행 이력이며 "
        "실제 Broker 주문을 수행하지 않습니다."
    )
