import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.sandbox_portfolio_valuation_refresh import (
    SandboxPortfolioValuationRefreshResult,
    SandboxPortfolioValuationSnapshot,
    verify_valuation_snapshot,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "sandbox_performance_snapshot"
)
REQUIRED_SNAPSHOT_TEXT = "RECORD IN MEMORY SANDBOX PERFORMANCE SNAPSHOT"
GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class SandboxPerformanceSnapshotPolicy:
    required_source_version: str = "V14.5"
    required_source_status: str = "VALUED_IN_MEMORY"
    required_valuation_status: str = "VALUED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_SNAPSHOT_TEXT
    maximum_history_count: int = 100
    require_same_operator: bool = True
    require_chronological_history: bool = True
    require_source_hash_validation: bool = True
    require_hash_chain: bool = True
    simulation_only: bool = True
    market_data_api_disabled: bool = True
    credentials_forbidden: bool = True
    account_access_disabled: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxPerformanceRecord:
    performance_record_id: str
    recorded_at: str
    sequence: int
    source_type: str
    source_id: str
    starting_equity: float
    total_equity: float
    period_profit_loss: float
    period_return_percent: float
    cumulative_profit_loss: float
    cumulative_return_percent: float
    running_peak_equity: float
    drawdown_amount: float
    drawdown_percent: float
    simulation_only: bool
    account_accessed: bool
    market_data_api_called: bool
    broker_api_called: bool
    live_execution_authorized: bool
    previous_record_hash: str
    record_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("record_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxPerformanceHistory:
    performance_history_id: str
    created_at: str
    history_status: str
    valuation_result_id: str
    valuation_snapshot_id: str
    valuation_snapshot_hash: str
    session_id: str
    operator: str
    record_count: int
    starting_equity: float
    current_equity: float
    peak_equity: float
    cumulative_profit_loss: float
    cumulative_return_percent: float
    current_drawdown_amount: float
    current_drawdown_percent: float
    maximum_drawdown_amount: float
    maximum_drawdown_percent: float
    records: tuple[SandboxPerformanceRecord, ...]
    credentials_used: bool
    market_data_api_called: bool
    network_accessed: bool
    account_accessed: bool
    account_updated: bool
    broker_api_called: bool
    order_submitted: bool
    live_execution_authorized: bool
    history_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["records"] = [record.to_dict() for record in self.records]
        payload.pop("history_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_without_hash()
        payload["history_hash"] = self.history_hash
        return payload


@dataclass
class SandboxPerformanceSnapshotResult:
    version: str
    created_at: str
    performance_result_id: str
    result_status: str
    result_status_label: str
    performance_history_id: str | None
    history_hash: str | None
    record_count: int
    starting_equity: float
    current_equity: float
    peak_equity: float
    cumulative_profit_loss: float
    cumulative_return_percent: float
    current_drawdown_percent: float
    maximum_drawdown_percent: float
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    valuation_checks_passed: bool
    chronology_checks_passed: bool
    calculation_checks_passed: bool
    record_hash_checks_passed: bool
    history_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    performance_snapshot_completed: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    market_data_api_called: bool
    network_accessed: bool
    account_accessed: bool
    account_updated: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    performance_policy: SandboxPerformanceSnapshotPolicy
    history: SandboxPerformanceHistory | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["performance_policy"] = self.performance_policy.to_dict()
        payload["history"] = self.history.to_dict() if self.history else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: SandboxPerformanceSnapshotPolicy) -> list[str]:
    if not isinstance(policy, SandboxPerformanceSnapshotPolicy):
        return ["Performance Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V14.5",
        "required_source_status": "VALUED_IN_MEMORY",
        "required_valuation_status": "VALUED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_SNAPSHOT_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V14.6 기준과 다릅니다.")
    if policy.maximum_history_count <= 0:
        errors.append("Maximum History Count가 올바르지 않습니다.")
    for name in (
        "require_same_operator", "require_chronological_history",
        "require_source_hash_validation", "require_hash_chain",
        "simulation_only", "market_data_api_disabled",
        "credentials_forbidden", "account_access_disabled",
        "network_access_disabled", "broker_api_disabled",
        "order_submission_disabled", "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V14.6에서 True여야 합니다.")
    return errors


def validate_source(
    source: Any,
) -> tuple[SandboxPortfolioValuationSnapshot | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, SandboxPortfolioValuationRefreshResult):
        return None, ["Source는 V14.5 Valuation Result여야 합니다."]
    if not (
        source.version == "V14.5"
        and source.result_status == "VALUED_IN_MEMORY"
        and source.all_checks_passed
        and source.valuation_refresh_completed
        and source.snapshot is not None
    ):
        errors.append("정상 V14.5 Valuation Source가 아닙니다.")
    if any((
        source.paper_execution_authorized,
        source.automatic_execution_authorized,
        not source.execution_blocked,
        source.credentials_used,
        source.market_data_api_called,
        source.network_accessed,
        source.account_accessed,
        source.account_updated,
        source.broker_api_called,
        source.order_submitted,
        source.live_execution_authorized,
    )):
        errors.append("V14.5 Source 실행 안전장치가 올바르지 않습니다.")
    snapshot = source.snapshot
    if snapshot:
        valid, verify_errors = verify_valuation_snapshot(snapshot)
        if not valid:
            errors.extend(verify_errors)
        if source.valuation_snapshot_id != snapshot.valuation_snapshot_id:
            errors.append("Valuation Snapshot ID 연결이 다릅니다.")
        if source.snapshot_hash != snapshot.snapshot_hash:
            errors.append("Valuation Snapshot Hash 연결이 다릅니다.")
    return snapshot, errors


def make_record(
    sequence: int,
    recorded_at: str,
    source_type: str,
    source_id: str,
    starting_equity: float,
    previous_equity: float,
    equity: float,
    peak: float,
    previous_hash: str,
) -> SandboxPerformanceRecord:
    period_profit = round(equity - previous_equity, 2)
    period_return = round(
        period_profit / previous_equity * 100 if previous_equity else 0.0,
        6,
    )
    cumulative_profit = round(equity - starting_equity, 2)
    cumulative_return = round(
        cumulative_profit / starting_equity * 100 if starting_equity else 0.0,
        6,
    )
    running_peak = max(peak, equity)
    drawdown = round(running_peak - equity, 2)
    drawdown_percent = round(
        drawdown / running_peak * 100 if running_peak else 0.0,
        6,
    )
    draft = SandboxPerformanceRecord(
        performance_record_id=str(uuid.uuid4()),
        recorded_at=recorded_at,
        sequence=sequence,
        source_type=source_type,
        source_id=source_id,
        starting_equity=starting_equity,
        total_equity=equity,
        period_profit_loss=period_profit,
        period_return_percent=period_return,
        cumulative_profit_loss=cumulative_profit,
        cumulative_return_percent=cumulative_return,
        running_peak_equity=running_peak,
        drawdown_amount=drawdown,
        drawdown_percent=drawdown_percent,
        simulation_only=True,
        account_accessed=False,
        market_data_api_called=False,
        broker_api_called=False,
        live_execution_authorized=False,
        previous_record_hash=previous_hash,
        record_hash="",
    )
    return SandboxPerformanceRecord(
        **{
            **asdict(draft),
            "record_hash": sha256_payload(draft.payload_without_hash()),
        }
    )


def verify_performance_record(
    record: SandboxPerformanceRecord,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if (
        record.total_equity < 0 or record.running_peak_equity < record.total_equity
        or record.drawdown_amount
        != round(record.running_peak_equity - record.total_equity, 2)
    ):
        errors.append(f"{record.sequence}: Performance 값이 올바르지 않습니다.")
    expected_drawdown = round(
        record.drawdown_amount / record.running_peak_equity * 100
        if record.running_peak_equity else 0.0,
        6,
    )
    if record.drawdown_percent != expected_drawdown:
        errors.append(f"{record.sequence}: Drawdown 계산이 다릅니다.")
    if any((
        not record.simulation_only, record.account_accessed,
        record.market_data_api_called, record.broker_api_called,
        record.live_execution_authorized,
    )):
        errors.append(f"{record.sequence}: 외부 실행 흔적이 있습니다.")
    if record.record_hash != sha256_payload(record.payload_without_hash()):
        errors.append(f"{record.sequence}: Record Hash가 다릅니다.")
    return not errors, errors


def verify_performance_history(
    history: SandboxPerformanceHistory,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if history.history_status != "RECORDED_IN_MEMORY":
        errors.append("Performance History 상태가 올바르지 않습니다.")
    if history.record_count != len(history.records) or not history.records:
        errors.append("Performance Record Count가 일치하지 않습니다.")
    previous_hash = GENESIS_HASH
    previous_time = ""
    seen: set[str] = set()
    for sequence, record in enumerate(history.records, start=1):
        if record.source_id in seen:
            errors.append("중복 Performance Source가 있습니다.")
        seen.add(record.source_id)
        if (
            record.sequence != sequence
            or record.previous_record_hash != previous_hash
            or (previous_time and record.recorded_at <= previous_time)
        ):
            errors.append(f"{sequence}: Performance 순서 또는 Hash Chain이 다릅니다.")
        valid, record_errors = verify_performance_record(record)
        if not valid:
            errors.extend(record_errors)
        previous_hash = record.record_hash
        previous_time = record.recorded_at
    if history.records:
        current = history.records[-1]
        if (
            history.starting_equity != history.records[0].starting_equity
            or history.current_equity != current.total_equity
            or history.peak_equity != max(x.total_equity for x in history.records)
            or history.cumulative_profit_loss != current.cumulative_profit_loss
            or history.current_drawdown_percent != current.drawdown_percent
            or history.maximum_drawdown_percent
            != max(x.drawdown_percent for x in history.records)
        ):
            errors.append("Performance History 집계가 일치하지 않습니다.")
    if any((
        history.credentials_used, history.market_data_api_called,
        history.network_accessed, history.account_accessed,
        history.account_updated, history.broker_api_called,
        history.order_submitted, history.live_execution_authorized,
    )):
        errors.append("Performance History에 외부 실행 흔적이 있습니다.")
    if history.history_hash != sha256_payload(history.payload_without_hash()):
        errors.append("Performance History Hash가 일치하지 않습니다.")
    return not errors, errors


def record_sandbox_performance_snapshot(
    source: SandboxPortfolioValuationRefreshResult,
    operator: str,
    confirmation_text: str,
    prior_equities: list[dict[str, Any]] | None = None,
    policy: SandboxPerformanceSnapshotPolicy | None = None,
    now: datetime | None = None,
) -> SandboxPerformanceSnapshotResult:
    policy = policy or SandboxPerformanceSnapshotPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("Performance 확인 문구가 일치하지 않습니다.")
    if prior_equities is None:
        prior_equities = []
    if not isinstance(prior_equities, list):
        prior_equities = []
        input_errors.append("Prior Equities는 list여야 합니다.")
    clean_prior: list[tuple[str, float, str]] = []
    seen_ids: set[str] = set()
    last_time = ""
    for index, item in enumerate(prior_equities, start=1):
        if not isinstance(item, dict):
            input_errors.append(f"{index}: Prior Equity 형식이 다릅니다.")
            continue
        timestamp = item.get("recorded_at")
        equity = item.get("total_equity")
        source_id = item.get("source_id")
        if (
            not isinstance(timestamp, str) or not timestamp
            or not isinstance(equity, (int, float)) or isinstance(equity, bool)
            or equity <= 0 or not isinstance(source_id, str) or not source_id
        ):
            input_errors.append(f"{index}: Prior Equity 값이 올바르지 않습니다.")
            continue
        if timestamp <= last_time or source_id in seen_ids:
            input_errors.append(f"{index}: Prior Equity 순서 또는 ID가 중복입니다.")
        last_time = timestamp
        seen_ids.add(source_id)
        clean_prior.append((timestamp, round(float(equity), 2), source_id))
    snapshot, source_errors = validate_source(source)
    if snapshot:
        if snapshot.operator != clean_operator:
            input_errors.append("Valuation Operator와 Performance Operator가 다릅니다.")
        if last_time and created_at <= last_time:
            input_errors.append("현재 Snapshot 시간이 Prior History 이후가 아닙니다.")
        if source.valuation_result_id in seen_ids:
            input_errors.append("현재 Valuation Source가 이미 기록되었습니다.")
    if len(clean_prior) + 1 > policy.maximum_history_count:
        input_errors.append("Maximum History Count를 초과했습니다.")

    records: tuple[SandboxPerformanceRecord, ...] = ()
    history: SandboxPerformanceHistory | None = None
    history_errors: list[str] = []
    preliminary_errors = policy_errors + input_errors + source_errors
    if not preliminary_errors and snapshot:
        data = clean_prior + [(
            created_at, snapshot.total_equity, source.valuation_result_id
        )]
        starting = data[0][1]
        previous_equity = starting
        peak = starting
        previous_hash = GENESIS_HASH
        values: list[SandboxPerformanceRecord] = []
        for sequence, (timestamp, equity, source_id) in enumerate(data, start=1):
            record = make_record(
                sequence, timestamp,
                "PRIOR_SIMULATED_EQUITY" if sequence <= len(clean_prior)
                else "V14.5_VALUATION",
                source_id, starting, previous_equity, equity,
                peak, previous_hash,
            )
            values.append(record)
            previous_equity = equity
            peak = record.running_peak_equity
            previous_hash = record.record_hash
        records = tuple(values)
        current = records[-1]
        draft = SandboxPerformanceHistory(
            performance_history_id=str(uuid.uuid4()),
            created_at=created_at,
            history_status="RECORDED_IN_MEMORY",
            valuation_result_id=source.valuation_result_id,
            valuation_snapshot_id=snapshot.valuation_snapshot_id,
            valuation_snapshot_hash=snapshot.snapshot_hash,
            session_id=snapshot.session_id,
            operator=clean_operator,
            record_count=len(records),
            starting_equity=starting,
            current_equity=current.total_equity,
            peak_equity=max(x.total_equity for x in records),
            cumulative_profit_loss=current.cumulative_profit_loss,
            cumulative_return_percent=current.cumulative_return_percent,
            current_drawdown_amount=current.drawdown_amount,
            current_drawdown_percent=current.drawdown_percent,
            maximum_drawdown_amount=max(x.drawdown_amount for x in records),
            maximum_drawdown_percent=max(x.drawdown_percent for x in records),
            records=records,
            credentials_used=False, market_data_api_called=False,
            network_accessed=False, account_accessed=False,
            account_updated=False, broker_api_called=False,
            order_submitted=False, live_execution_authorized=False,
            history_hash="",
        )
        history = SandboxPerformanceHistory(
            **{
                **asdict(draft), "records": draft.records,
                "history_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
        valid, history_errors = verify_performance_history(history)
        if not valid:
            history_errors = list(history_errors)
    all_errors = preliminary_errors + history_errors
    passed = bool(history) and not all_errors
    status = "RECORDED_IN_MEMORY" if passed else (
        "BLOCKED" if not source_errors else "FAILED"
    )
    hash_ok = bool(history) and not history_errors
    return SandboxPerformanceSnapshotResult(
        version="V14.6", created_at=created_at,
        performance_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "RECORDED_IN_MEMORY": "Sandbox Performance Snapshot 기록 완료",
            "BLOCKED": "Performance 입력 또는 이력 차단",
            "FAILED": "V14.5 Source 검증 실패",
        }[status],
        performance_history_id=history.performance_history_id if history else None,
        history_hash=history.history_hash if history else None,
        record_count=len(records),
        starting_equity=history.starting_equity if history else 0.0,
        current_equity=history.current_equity if history else 0.0,
        peak_equity=history.peak_equity if history else 0.0,
        cumulative_profit_loss=history.cumulative_profit_loss if history else 0.0,
        cumulative_return_percent=history.cumulative_return_percent if history else 0.0,
        current_drawdown_percent=history.current_drawdown_percent if history else 0.0,
        maximum_drawdown_percent=history.maximum_drawdown_percent if history else 0.0,
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=not source_errors,
        valuation_checks_passed=bool(snapshot) and not source_errors,
        chronology_checks_passed=bool(records) and not input_errors,
        calculation_checks_passed=passed,
        record_hash_checks_passed=hash_ok,
        history_hash_checks_passed=hash_ok,
        safety_checks_passed=not policy_errors,
        all_checks_passed=passed,
        performance_snapshot_completed=passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        credentials_used=False, market_data_api_called=False,
        network_accessed=False, account_accessed=False,
        account_updated=False, broker_api_called=False,
        broker_order_created=False, order_submitted=False,
        live_order_created=False, live_execution_authorized=False,
        performance_policy=policy, history=history,
        reasons=[
            "가상 Equity 이력과 Drawdown을 In-Memory로 기록했습니다."
            if passed else "Sandbox Performance Snapshot이 차단되었습니다."
        ],
        warnings=all_errors + [
            "성과 이력은 Simulation이며 실제 투자 성과가 아닙니다."
        ],
        next_actions=[
            "수익률, Peak Equity, Drawdown 및 Hash Chain을 확인합니다.",
            "실제 계좌 성과나 투자 판단 자료로 사용하지 않습니다.",
        ],
    )


def save_performance_result(
    result: SandboxPerformanceSnapshotResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"sandbox_performance_{stamp}.json"
    latest = directory / "latest_sandbox_performance.json"
    payload = result.to_dict()
    for path in (report, latest):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_performance_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V14.6":
        raise ValueError("V14.6 결과 파일이 아닙니다.")
    raw = payload.get("history")
    if raw:
        history = SandboxPerformanceHistory(
            **{
                **raw,
                "records": tuple(
                    SandboxPerformanceRecord(**item)
                    for item in raw.get("records", [])
                ),
            }
        )
        valid, errors = verify_performance_history(history)
        if not valid:
            raise ValueError(
                "저장된 Performance History가 올바르지 않습니다: "
                + "; ".join(errors)
            )
    return payload
