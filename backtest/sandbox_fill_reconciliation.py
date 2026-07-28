import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.sandbox_order_lifecycle_tracker import (
    SandboxOrderLifecycle,
    SandboxOrderLifecycleBatch,
    SandboxOrderLifecycleTrackerResult,
    verify_lifecycle,
    verify_lifecycle_batch,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "sandbox_fill_reconciliation"
)
REQUIRED_RECONCILE_TEXT = "RECONCILE IN MEMORY SANDBOX FILLS"
RECONCILED_STATES = {"FILLED_SIMULATED", "CANCELLED_SIMULATED"}


@dataclass(frozen=True)
class SandboxFillReconciliationPolicy:
    required_source_version: str = "V14.2"
    required_source_status: str = "TRACKED_IN_MEMORY"
    required_batch_status: str = "TRACKED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_RECONCILE_TEXT
    maximum_order_count: int = 20
    require_same_operator: bool = True
    require_exact_order_set: bool = True
    require_source_hash_validation: bool = True
    require_quantity_match: bool = True
    require_terminal_state_match: bool = True
    require_fill_price_match: bool = True
    require_reconciliation_hash: bool = True
    allow_partial_fills: bool = False
    simulation_only: bool = True
    credentials_forbidden: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxFillReconciliationItem:
    reconciliation_item_id: str
    reconciled_at: str
    client_order_id: str
    lifecycle_id: str
    lifecycle_hash: str
    dispatch_request_id: str
    dispatch_request_hash: str
    dispatch_receipt_id: str
    dispatch_receipt_hash: str
    instrument: str
    side: str
    order_kind: str
    expected_quantity: int
    lifecycle_filled_quantity: int
    lifecycle_remaining_quantity: int
    calculated_quantity: int
    expected_terminal_state: str
    observed_terminal_state: str
    expected_fill_price: float | None
    observed_fill_price: float | None
    quantity_matches: bool
    terminal_state_matches: bool
    fill_price_matches: bool
    event_chain_matches: bool
    source_links_match: bool
    reconciliation_status: str
    simulation_only: bool
    broker_fill_received: bool
    broker_order_id: str | None
    order_submitted: bool
    live_execution_authorized: bool
    item_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("item_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxFillReconciliationReport:
    reconciliation_report_id: str
    created_at: str
    reconciliation_status: str
    tracker_result_id: str
    lifecycle_batch_id: str
    lifecycle_batch_hash: str
    session_id: str
    operator: str
    order_count: int
    reconciled_count: int
    filled_count: int
    cancelled_count: int
    mismatch_count: int
    items: tuple[SandboxFillReconciliationItem, ...]
    credentials_used: bool
    dns_lookup_performed: bool
    socket_created: bool
    http_request_sent: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    report_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [item.to_dict() for item in self.items]
        payload.pop("report_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [item.to_dict() for item in self.items]
        return payload


@dataclass
class SandboxFillReconciliationResult:
    version: str
    created_at: str
    reconciliation_result_id: str
    result_status: str
    result_status_label: str
    reconciliation_report_id: str | None
    report_hash: str | None
    order_count: int
    reconciled_count: int
    filled_count: int
    cancelled_count: int
    mismatch_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    lifecycle_checks_passed: bool
    identity_checks_passed: bool
    quantity_checks_passed: bool
    state_checks_passed: bool
    price_checks_passed: bool
    item_hash_checks_passed: bool
    report_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    reconciliation_completed: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    credentials_used: bool
    dns_lookup_performed: bool
    socket_created: bool
    http_request_sent: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    reconciliation_policy: SandboxFillReconciliationPolicy
    report: SandboxFillReconciliationReport | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reconciliation_policy"] = self.reconciliation_policy.to_dict()
        payload["report"] = self.report.to_dict() if self.report else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(
    policy: SandboxFillReconciliationPolicy,
) -> list[str]:
    if not isinstance(policy, SandboxFillReconciliationPolicy):
        return ["Reconciliation Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V14.2",
        "required_source_status": "TRACKED_IN_MEMORY",
        "required_batch_status": "TRACKED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_RECONCILE_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V14.3 기준과 다릅니다.")
    if policy.maximum_order_count <= 0:
        errors.append("Maximum Order Count가 올바르지 않습니다.")
    if policy.allow_partial_fills:
        errors.append("V14.3에서는 Partial Fill을 허용하지 않습니다.")
    for name in (
        "require_same_operator",
        "require_exact_order_set",
        "require_source_hash_validation",
        "require_quantity_match",
        "require_terminal_state_match",
        "require_fill_price_match",
        "require_reconciliation_hash",
        "simulation_only",
        "credentials_forbidden",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V14.3에서 True여야 합니다.")
    return errors


def validate_source(
    source: Any,
) -> tuple[SandboxOrderLifecycleBatch | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, SandboxOrderLifecycleTrackerResult):
        return None, ["Source는 V14.2 Lifecycle Tracker Result여야 합니다."]
    if not (
        source.version == "V14.2"
        and source.result_status == "TRACKED_IN_MEMORY"
        and source.all_checks_passed
        and source.lifecycle_tracking_completed
        and source.batch is not None
    ):
        errors.append("정상 V14.2 Lifecycle Source가 아닙니다.")
    if any((
        source.paper_execution_authorized,
        source.automatic_execution_authorized,
        not source.execution_blocked,
        source.credentials_used,
        source.dns_lookup_performed,
        source.socket_created,
        source.http_request_sent,
        source.network_accessed,
        source.account_accessed,
        source.broker_api_called,
        source.broker_order_created,
        source.order_submitted,
        source.live_order_created,
        source.live_execution_authorized,
    )):
        errors.append("V14.2 Source 실행 안전장치가 올바르지 않습니다.")
    batch = source.batch
    if batch:
        valid, verify_errors = verify_lifecycle_batch(batch)
        if not valid:
            errors.extend(verify_errors)
        if source.lifecycle_batch_id != batch.lifecycle_batch_id:
            errors.append("Lifecycle Batch ID 연결이 다릅니다.")
        if source.batch_hash != batch.batch_hash:
            errors.append("Lifecycle Batch Hash 연결이 다릅니다.")
    return batch, errors


def expected_values(
    lifecycle: SandboxOrderLifecycle,
) -> tuple[int, int, float | None]:
    if lifecycle.terminal_state == "FILLED_SIMULATED":
        return lifecycle.order_quantity, 0, lifecycle.average_fill_price
    return 0, lifecycle.order_quantity, None


def build_item(
    lifecycle: SandboxOrderLifecycle,
    reconciled_at: str,
) -> SandboxFillReconciliationItem:
    expected_filled, expected_remaining, expected_price = expected_values(
        lifecycle
    )
    event_valid, _ = verify_lifecycle(lifecycle)
    terminal_event = lifecycle.events[-1]
    quantity_matches = (
        lifecycle.filled_quantity == expected_filled
        and lifecycle.remaining_quantity == expected_remaining
        and terminal_event.filled_quantity == expected_filled
        and terminal_event.remaining_quantity == expected_remaining
        and expected_filled + expected_remaining == lifecycle.order_quantity
    )
    state_matches = (
        lifecycle.terminal_state in RECONCILED_STATES
        and terminal_event.current_state == lifecycle.terminal_state
    )
    price_matches = (
        lifecycle.average_fill_price == expected_price
        and terminal_event.simulated_fill_price == expected_price
    )
    source_links_match = all((
        bool(lifecycle.dispatch_request_id),
        bool(lifecycle.dispatch_request_hash),
        bool(lifecycle.dispatch_receipt_id),
        bool(lifecycle.dispatch_receipt_hash),
    ))
    passed = all((
        quantity_matches,
        state_matches,
        price_matches,
        event_valid,
        source_links_match,
    ))
    draft = SandboxFillReconciliationItem(
        reconciliation_item_id=str(uuid.uuid4()),
        reconciled_at=reconciled_at,
        client_order_id=lifecycle.client_order_id,
        lifecycle_id=lifecycle.lifecycle_id,
        lifecycle_hash=lifecycle.lifecycle_hash,
        dispatch_request_id=lifecycle.dispatch_request_id,
        dispatch_request_hash=lifecycle.dispatch_request_hash,
        dispatch_receipt_id=lifecycle.dispatch_receipt_id,
        dispatch_receipt_hash=lifecycle.dispatch_receipt_hash,
        instrument=lifecycle.instrument,
        side=lifecycle.side,
        order_kind=lifecycle.order_kind,
        expected_quantity=lifecycle.order_quantity,
        lifecycle_filled_quantity=lifecycle.filled_quantity,
        lifecycle_remaining_quantity=lifecycle.remaining_quantity,
        calculated_quantity=(
            lifecycle.filled_quantity + lifecycle.remaining_quantity
        ),
        expected_terminal_state=lifecycle.terminal_state,
        observed_terminal_state=terminal_event.current_state,
        expected_fill_price=expected_price,
        observed_fill_price=terminal_event.simulated_fill_price,
        quantity_matches=quantity_matches,
        terminal_state_matches=state_matches,
        fill_price_matches=price_matches,
        event_chain_matches=event_valid,
        source_links_match=source_links_match,
        reconciliation_status=(
            "RECONCILED_IN_MEMORY" if passed else "MISMATCH"
        ),
        simulation_only=True,
        broker_fill_received=False,
        broker_order_id=None,
        order_submitted=False,
        live_execution_authorized=False,
        item_hash="",
    )
    return SandboxFillReconciliationItem(
        **{
            **asdict(draft),
            "item_hash": sha256_payload(draft.payload_without_hash()),
        }
    )


def verify_reconciliation_item(
    item: SandboxFillReconciliationItem,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if item.reconciliation_status != "RECONCILED_IN_MEMORY":
        errors.append(f"{item.client_order_id}: Reconciliation 상태가 다릅니다.")
    if not all((
        item.quantity_matches,
        item.terminal_state_matches,
        item.fill_price_matches,
        item.event_chain_matches,
        item.source_links_match,
    )):
        errors.append(f"{item.client_order_id}: 대조 항목이 일치하지 않습니다.")
    if item.expected_terminal_state not in RECONCILED_STATES:
        errors.append(f"{item.client_order_id}: Terminal State가 허용되지 않습니다.")
    if item.calculated_quantity != item.expected_quantity:
        errors.append(f"{item.client_order_id}: 수량 합계가 다릅니다.")
    if item.expected_terminal_state == "FILLED_SIMULATED":
        if not (
            item.lifecycle_filled_quantity == item.expected_quantity
            and item.lifecycle_remaining_quantity == 0
            and item.expected_fill_price is not None
            and item.expected_fill_price > 0
            and item.observed_fill_price == item.expected_fill_price
        ):
            errors.append(f"{item.client_order_id}: 모의 체결 대조가 다릅니다.")
    if item.expected_terminal_state == "CANCELLED_SIMULATED":
        if not (
            item.lifecycle_filled_quantity == 0
            and item.lifecycle_remaining_quantity == item.expected_quantity
            and item.expected_fill_price is None
            and item.observed_fill_price is None
        ):
            errors.append(f"{item.client_order_id}: 모의 취소 대조가 다릅니다.")
    if any((
        not item.simulation_only,
        item.broker_fill_received,
        item.broker_order_id is not None,
        item.order_submitted,
        item.live_execution_authorized,
    )):
        errors.append(f"{item.client_order_id}: 실제 실행 흔적이 있습니다.")
    if item.item_hash != sha256_payload(item.payload_without_hash()):
        errors.append(f"{item.client_order_id}: Item Hash가 다릅니다.")
    return not errors, errors


def verify_reconciliation_report(
    report: SandboxFillReconciliationReport,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if report.reconciliation_status != "RECONCILED_IN_MEMORY":
        errors.append("Reconciliation Report 상태가 올바르지 않습니다.")
    if report.order_count != len(report.items) or not report.items:
        errors.append("Reconciliation Order Count가 일치하지 않습니다.")
    if report.reconciled_count != report.order_count:
        errors.append("Reconciled Count가 일치하지 않습니다.")
    if (
        report.filled_count + report.cancelled_count != report.order_count
        or report.mismatch_count != 0
    ):
        errors.append("Reconciliation 집계가 일치하지 않습니다.")
    ids: set[str] = set()
    for item in report.items:
        if item.client_order_id in ids:
            errors.append("중복 Reconciliation Order ID가 있습니다.")
        ids.add(item.client_order_id)
        valid, item_errors = verify_reconciliation_item(item)
        if not valid:
            errors.extend(item_errors)
    if any((
        report.credentials_used,
        report.dns_lookup_performed,
        report.socket_created,
        report.http_request_sent,
        report.network_accessed,
        report.account_accessed,
        report.broker_api_called,
        report.broker_order_created,
        report.order_submitted,
        report.live_order_created,
        report.live_execution_authorized,
    )):
        errors.append("Reconciliation Report에 외부 실행 흔적이 있습니다.")
    if report.report_hash != sha256_payload(report.payload_without_hash()):
        errors.append("Reconciliation Report Hash가 일치하지 않습니다.")
    return not errors, errors


def reconcile_sandbox_fills(
    source: SandboxOrderLifecycleTrackerResult,
    operator: str,
    confirmation_text: str,
    policy: SandboxFillReconciliationPolicy | None = None,
    now: datetime | None = None,
) -> SandboxFillReconciliationResult:
    policy = policy or SandboxFillReconciliationPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("Reconciliation 확인 문구가 일치하지 않습니다.")
    source_batch, source_errors = validate_source(source)
    lifecycle_errors: list[str] = []
    if source_batch:
        if source_batch.operator != clean_operator:
            input_errors.append("Lifecycle Operator와 Reconciliation Operator가 다릅니다.")
        if source_batch.order_count > policy.maximum_order_count:
            input_errors.append("허용된 최대 주문 수를 초과했습니다.")
        for lifecycle in source_batch.lifecycles:
            valid, errors = verify_lifecycle(lifecycle)
            if not valid:
                lifecycle_errors.extend(errors)

    items: tuple[SandboxFillReconciliationItem, ...] = ()
    report: SandboxFillReconciliationReport | None = None
    report_errors: list[str] = []
    preliminary_errors = (
        policy_errors + input_errors + source_errors + lifecycle_errors
    )
    if not preliminary_errors and source_batch:
        items = tuple(
            build_item(lifecycle, created_at)
            for lifecycle in source_batch.lifecycles
        )
        mismatch_count = sum(
            item.reconciliation_status != "RECONCILED_IN_MEMORY"
            for item in items
        )
        draft = SandboxFillReconciliationReport(
            reconciliation_report_id=str(uuid.uuid4()),
            created_at=created_at,
            reconciliation_status=(
                "RECONCILED_IN_MEMORY" if mismatch_count == 0 else "MISMATCH"
            ),
            tracker_result_id=source.tracker_result_id,
            lifecycle_batch_id=source_batch.lifecycle_batch_id,
            lifecycle_batch_hash=source_batch.batch_hash,
            session_id=source_batch.session_id,
            operator=clean_operator,
            order_count=len(items),
            reconciled_count=sum(
                item.reconciliation_status == "RECONCILED_IN_MEMORY"
                for item in items
            ),
            filled_count=sum(
                item.expected_terminal_state == "FILLED_SIMULATED"
                for item in items
            ),
            cancelled_count=sum(
                item.expected_terminal_state == "CANCELLED_SIMULATED"
                for item in items
            ),
            mismatch_count=mismatch_count,
            items=items,
            credentials_used=False,
            dns_lookup_performed=False,
            socket_created=False,
            http_request_sent=False,
            network_accessed=False,
            account_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_order_created=False,
            live_execution_authorized=False,
            report_hash="",
        )
        report = SandboxFillReconciliationReport(
            **{
                **asdict(draft),
                "items": draft.items,
                "report_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
        valid, report_errors = verify_reconciliation_report(report)
        if not valid:
            report_errors = list(report_errors)

    all_errors = preliminary_errors + report_errors
    passed = bool(report) and not all_errors
    status = "RECONCILED_IN_MEMORY" if passed else (
        "BLOCKED" if not source_errors else "FAILED"
    )
    quantity_ok = bool(items) and all(item.quantity_matches for item in items)
    state_ok = bool(items) and all(
        item.terminal_state_matches for item in items
    )
    price_ok = bool(items) and all(item.fill_price_matches for item in items)
    hash_ok = bool(report) and not report_errors
    return SandboxFillReconciliationResult(
        version="V14.3",
        created_at=created_at,
        reconciliation_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "RECONCILED_IN_MEMORY": "Sandbox Fill 대조 완료",
            "BLOCKED": "Reconciliation 입력 또는 대조 차단",
            "FAILED": "V14.2 Source 검증 실패",
        }[status],
        reconciliation_report_id=(
            report.reconciliation_report_id if report else None
        ),
        report_hash=report.report_hash if report else None,
        order_count=len(items),
        reconciled_count=report.reconciled_count if report else 0,
        filled_count=report.filled_count if report else 0,
        cancelled_count=report.cancelled_count if report else 0,
        mismatch_count=report.mismatch_count if report else 0,
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=not source_errors,
        lifecycle_checks_passed=bool(source_batch) and not lifecycle_errors,
        identity_checks_passed=bool(items) and all(
            item.source_links_match for item in items
        ),
        quantity_checks_passed=quantity_ok,
        state_checks_passed=state_ok,
        price_checks_passed=price_ok,
        item_hash_checks_passed=hash_ok,
        report_hash_checks_passed=hash_ok,
        safety_checks_passed=not policy_errors,
        all_checks_passed=passed,
        reconciliation_completed=passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        credentials_used=False,
        dns_lookup_performed=False,
        socket_created=False,
        http_request_sent=False,
        network_accessed=False,
        account_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        reconciliation_policy=policy,
        report=report,
        reasons=[
            "V14.2 Lifecycle과 모의 체결·취소 결과를 1:1 대조했습니다."
            if passed else "Sandbox Fill Reconciliation이 차단되었습니다."
        ],
        warnings=all_errors + [
            "모든 Fill은 Simulation이며 실제 Broker 체결 정보가 아닙니다."
        ],
        next_actions=[
            "수량·상태·가격 및 Source Hash 연결을 수동 확인합니다.",
            "실제 Broker API 또는 계좌 정보로 해석하지 않습니다.",
        ],
    )


def save_reconciliation_result(
    result: SandboxFillReconciliationResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"sandbox_fill_reconciliation_{stamp}.json"
    latest = directory / "latest_sandbox_fill_reconciliation.json"
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


def load_reconciliation_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V14.3":
        raise ValueError("V14.3 결과 파일이 아닙니다.")
    raw = payload.get("report")
    if raw:
        report = SandboxFillReconciliationReport(
            **{
                **raw,
                "items": tuple(
                    SandboxFillReconciliationItem(**item)
                    for item in raw.get("items", [])
                ),
            }
        )
        valid, errors = verify_reconciliation_report(report)
        if not valid:
            raise ValueError(
                "저장된 Reconciliation Report가 올바르지 않습니다: "
                + "; ".join(errors)
            )
    return payload
