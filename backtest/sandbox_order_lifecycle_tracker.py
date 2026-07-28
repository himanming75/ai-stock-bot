import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.sandbox_paper_order_dispatcher import (
    SandboxDispatchBatch,
    SandboxDispatchReceipt,
    SandboxDispatchRequest,
    SandboxPaperOrderDispatcherResult,
    verify_dispatch_batch,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "sandbox_order_lifecycle_tracker"
)
REQUIRED_TRACK_TEXT = "TRACK IN MEMORY SANDBOX ORDER LIFECYCLE"
GENESIS_HASH = "0" * 64
TERMINAL_STATES = {"FILLED_SIMULATED", "CANCELLED_SIMULATED"}


@dataclass(frozen=True)
class SandboxOrderLifecyclePolicy:
    required_source_version: str = "V14.1"
    required_source_status: str = "DISPATCHED_IN_MEMORY"
    required_dispatch_status: str = "DISPATCHED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_TRACK_TEXT
    maximum_order_count: int = 20
    require_same_operator: bool = True
    require_exact_order_set: bool = True
    require_three_events_per_order: bool = True
    require_event_hash_chain: bool = True
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
class SandboxOrderLifecycleEvent:
    event_id: str
    occurred_at: str
    sequence: int
    client_order_id: str
    previous_state: str | None
    current_state: str
    event_type: str
    order_quantity: int
    filled_quantity: int
    remaining_quantity: int
    simulated_fill_price: float | None
    simulation_only: bool
    broker_event_received: bool
    previous_event_hash: str
    event_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("event_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxOrderLifecycle:
    lifecycle_id: str
    created_at: str
    client_order_id: str
    dispatch_request_id: str
    dispatch_request_hash: str
    dispatch_receipt_id: str
    dispatch_receipt_hash: str
    instrument: str
    side: str
    order_kind: str
    order_quantity: int
    terminal_state: str
    filled_quantity: int
    remaining_quantity: int
    average_fill_price: float | None
    event_count: int
    events: tuple[SandboxOrderLifecycleEvent, ...]
    broker_order_id: str | None
    order_submitted: bool
    live_execution_authorized: bool
    lifecycle_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["events"] = [event.to_dict() for event in self.events]
        payload.pop("lifecycle_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["events"] = [event.to_dict() for event in self.events]
        return payload


@dataclass(frozen=True)
class SandboxOrderLifecycleBatch:
    lifecycle_batch_id: str
    created_at: str
    lifecycle_status: str
    dispatcher_result_id: str
    dispatch_batch_id: str
    dispatch_batch_hash: str
    session_id: str
    operator: str
    order_count: int
    filled_count: int
    cancelled_count: int
    lifecycles: tuple[SandboxOrderLifecycle, ...]
    credentials_used: bool
    dns_lookup_performed: bool
    socket_created: bool
    http_request_sent: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    batch_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["lifecycles"] = [
            lifecycle.to_dict() for lifecycle in self.lifecycles
        ]
        payload.pop("batch_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["lifecycles"] = [
            lifecycle.to_dict() for lifecycle in self.lifecycles
        ]
        return payload


@dataclass
class SandboxOrderLifecycleTrackerResult:
    version: str
    created_at: str
    tracker_result_id: str
    result_status: str
    result_status_label: str
    lifecycle_batch_id: str | None
    batch_hash: str | None
    order_count: int
    filled_count: int
    cancelled_count: int
    event_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    dispatch_checks_passed: bool
    plan_checks_passed: bool
    transition_checks_passed: bool
    event_hash_checks_passed: bool
    lifecycle_hash_checks_passed: bool
    batch_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    lifecycle_tracking_completed: bool
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
    lifecycle_policy: SandboxOrderLifecyclePolicy
    batch: SandboxOrderLifecycleBatch | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["lifecycle_policy"] = self.lifecycle_policy.to_dict()
        payload["batch"] = self.batch.to_dict() if self.batch else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: SandboxOrderLifecyclePolicy) -> list[str]:
    if not isinstance(policy, SandboxOrderLifecyclePolicy):
        return ["Lifecycle Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V14.1",
        "required_source_status": "DISPATCHED_IN_MEMORY",
        "required_dispatch_status": "DISPATCHED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_TRACK_TEXT,
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V14.2 기준과 다릅니다.")
    if policy.maximum_order_count <= 0:
        errors.append("Maximum Order Count가 올바르지 않습니다.")
    if policy.allow_partial_fills:
        errors.append("V14.2에서는 Partial Fill을 허용하지 않습니다.")
    for name in (
        "require_same_operator",
        "require_exact_order_set",
        "require_three_events_per_order",
        "require_event_hash_chain",
        "simulation_only",
        "credentials_forbidden",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V14.2에서 True여야 합니다.")
    return errors


def validate_source(
    source: Any,
) -> tuple[SandboxDispatchBatch | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, SandboxPaperOrderDispatcherResult):
        return None, ["Source는 V14.1 Dispatcher Result여야 합니다."]
    if not (
        source.version == "V14.1"
        and source.result_status == "DISPATCHED_IN_MEMORY"
        and source.all_checks_passed
        and source.sandbox_dispatch_completed
        and source.batch is not None
    ):
        errors.append("정상 V14.1 Dispatcher Source가 아닙니다.")
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
        errors.append("V14.1 Source 실행 안전장치가 올바르지 않습니다.")
    batch = source.batch
    if batch:
        valid, verify_errors = verify_dispatch_batch(batch)
        if not valid:
            errors.extend(verify_errors)
        if source.dispatch_batch_id != batch.dispatch_batch_id:
            errors.append("Dispatch Batch ID 연결이 다릅니다.")
        if source.batch_hash != batch.batch_hash:
            errors.append("Dispatch Batch Hash 연결이 다릅니다.")
    return batch, errors


def make_event(
    created_at: str,
    sequence: int,
    client_order_id: str,
    previous_state: str | None,
    current_state: str,
    quantity: int,
    filled_quantity: int,
    price: float | None,
    previous_hash: str,
) -> SandboxOrderLifecycleEvent:
    draft = SandboxOrderLifecycleEvent(
        event_id=str(uuid.uuid4()),
        occurred_at=created_at,
        sequence=sequence,
        client_order_id=client_order_id,
        previous_state=previous_state,
        current_state=current_state,
        event_type="SIMULATED_STATE_TRANSITION",
        order_quantity=quantity,
        filled_quantity=filled_quantity,
        remaining_quantity=quantity - filled_quantity,
        simulated_fill_price=price,
        simulation_only=True,
        broker_event_received=False,
        previous_event_hash=previous_hash,
        event_hash="",
    )
    return SandboxOrderLifecycleEvent(
        **{
            **asdict(draft),
            "event_hash": sha256_payload(draft.payload_without_hash()),
        }
    )


def build_lifecycle(
    request: SandboxDispatchRequest,
    receipt: SandboxDispatchReceipt,
    terminal_state: str,
    fill_price: float | None,
    created_at: str,
) -> SandboxOrderLifecycle:
    quantity = request.quantity
    terminal_filled = quantity if terminal_state == "FILLED_SIMULATED" else 0
    terminal_price = fill_price if terminal_filled else None
    event1 = make_event(
        created_at, 1, request.client_order_id, None,
        "QUEUED_IN_MEMORY", quantity, 0, None, GENESIS_HASH,
    )
    event2 = make_event(
        created_at, 2, request.client_order_id, "QUEUED_IN_MEMORY",
        "ACKNOWLEDGED_IN_MEMORY", quantity, 0, None, event1.event_hash,
    )
    event3 = make_event(
        created_at, 3, request.client_order_id, "ACKNOWLEDGED_IN_MEMORY",
        terminal_state, quantity, terminal_filled, terminal_price,
        event2.event_hash,
    )
    events = (event1, event2, event3)
    draft = SandboxOrderLifecycle(
        lifecycle_id=str(uuid.uuid4()),
        created_at=created_at,
        client_order_id=request.client_order_id,
        dispatch_request_id=request.dispatch_request_id,
        dispatch_request_hash=request.request_hash,
        dispatch_receipt_id=receipt.dispatch_receipt_id,
        dispatch_receipt_hash=receipt.receipt_hash,
        instrument=request.instrument,
        side=request.side,
        order_kind=request.order_kind,
        order_quantity=quantity,
        terminal_state=terminal_state,
        filled_quantity=terminal_filled,
        remaining_quantity=quantity - terminal_filled,
        average_fill_price=terminal_price,
        event_count=len(events),
        events=events,
        broker_order_id=None,
        order_submitted=False,
        live_execution_authorized=False,
        lifecycle_hash="",
    )
    return SandboxOrderLifecycle(
        **{
            **asdict(draft),
            "events": draft.events,
            "lifecycle_hash": sha256_payload(draft.payload_without_hash()),
        }
    )


def verify_lifecycle(
    lifecycle: SandboxOrderLifecycle,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if lifecycle.event_count != 3 or len(lifecycle.events) != 3:
        errors.append(f"{lifecycle.client_order_id}: Event 수가 3개가 아닙니다.")
        return False, errors
    expected_states = (
        "QUEUED_IN_MEMORY",
        "ACKNOWLEDGED_IN_MEMORY",
        lifecycle.terminal_state,
    )
    previous_hash = GENESIS_HASH
    previous_state: str | None = None
    for sequence, (event, expected_state) in enumerate(
        zip(lifecycle.events, expected_states), start=1
    ):
        if (
            event.sequence != sequence
            or event.current_state != expected_state
            or event.previous_state != previous_state
        ):
            errors.append(f"{lifecycle.client_order_id}: 상태 전이 순서가 다릅니다.")
        if event.previous_event_hash != previous_hash:
            errors.append(f"{lifecycle.client_order_id}: Event Chain이 끊겼습니다.")
        if event.event_hash != sha256_payload(event.payload_without_hash()):
            errors.append(f"{lifecycle.client_order_id}: Event Hash가 다릅니다.")
        if not event.simulation_only or event.broker_event_received:
            errors.append(f"{lifecycle.client_order_id}: 실제 Broker Event 흔적이 있습니다.")
        previous_hash = event.event_hash
        previous_state = event.current_state
    if lifecycle.terminal_state not in TERMINAL_STATES:
        errors.append(f"{lifecycle.client_order_id}: Terminal State가 허용되지 않습니다.")
    if lifecycle.terminal_state == "FILLED_SIMULATED":
        if not (
            lifecycle.filled_quantity == lifecycle.order_quantity
            and lifecycle.remaining_quantity == 0
            and lifecycle.average_fill_price is not None
            and lifecycle.average_fill_price > 0
        ):
            errors.append(f"{lifecycle.client_order_id}: 모의 체결 값이 다릅니다.")
    if lifecycle.terminal_state == "CANCELLED_SIMULATED":
        if not (
            lifecycle.filled_quantity == 0
            and lifecycle.remaining_quantity == lifecycle.order_quantity
            and lifecycle.average_fill_price is None
        ):
            errors.append(f"{lifecycle.client_order_id}: 모의 취소 값이 다릅니다.")
    if any((
        lifecycle.broker_order_id is not None,
        lifecycle.order_submitted,
        lifecycle.live_execution_authorized,
    )):
        errors.append(f"{lifecycle.client_order_id}: 실제 실행 흔적이 있습니다.")
    if lifecycle.lifecycle_hash != sha256_payload(
        lifecycle.payload_without_hash()
    ):
        errors.append(f"{lifecycle.client_order_id}: Lifecycle Hash가 다릅니다.")
    return not errors, errors


def verify_lifecycle_batch(
    batch: SandboxOrderLifecycleBatch,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if batch.lifecycle_status != "TRACKED_IN_MEMORY":
        errors.append("Lifecycle Batch 상태가 올바르지 않습니다.")
    if batch.order_count != len(batch.lifecycles) or not batch.lifecycles:
        errors.append("Lifecycle Order Count가 일치하지 않습니다.")
    if batch.filled_count + batch.cancelled_count != batch.order_count:
        errors.append("Terminal State Count가 일치하지 않습니다.")
    ids: set[str] = set()
    for lifecycle in batch.lifecycles:
        if lifecycle.client_order_id in ids:
            errors.append("중복 Lifecycle Order ID가 있습니다.")
        ids.add(lifecycle.client_order_id)
        valid, lifecycle_errors = verify_lifecycle(lifecycle)
        if not valid:
            errors.extend(lifecycle_errors)
    if any((
        batch.credentials_used,
        batch.dns_lookup_performed,
        batch.socket_created,
        batch.http_request_sent,
        batch.network_accessed,
        batch.broker_api_called,
        batch.broker_order_created,
        batch.order_submitted,
        batch.live_execution_authorized,
    )):
        errors.append("Lifecycle Batch에 외부 실행 흔적이 있습니다.")
    if batch.batch_hash != sha256_payload(batch.payload_without_hash()):
        errors.append("Lifecycle Batch Hash가 일치하지 않습니다.")
    return not errors, errors


def track_sandbox_order_lifecycle(
    source: SandboxPaperOrderDispatcherResult,
    operator: str,
    confirmation_text: str,
    terminal_states: dict[str, str],
    fill_prices: dict[str, float] | None = None,
    policy: SandboxOrderLifecyclePolicy | None = None,
    now: datetime | None = None,
) -> SandboxOrderLifecycleTrackerResult:
    policy = policy or SandboxOrderLifecyclePolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    fill_prices = fill_prices or {}
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("Lifecycle 확인 문구가 일치하지 않습니다.")
    source_batch, source_errors = validate_source(source)
    dispatch_errors: list[str] = []
    if source_batch and source_batch.operator != clean_operator:
        dispatch_errors.append("Dispatch Operator와 Tracker Operator가 다릅니다.")
    plan_errors: list[str] = []
    if not isinstance(terminal_states, dict):
        terminal_states = {}
        plan_errors.append("Terminal States는 dict여야 합니다.")
    if source_batch:
        order_ids = {item.client_order_id for item in source_batch.requests}
        if set(terminal_states) != order_ids:
            plan_errors.append("Terminal State 대상 주문이 Dispatch 주문과 다릅니다.")
        for order_id, state in terminal_states.items():
            if state not in TERMINAL_STATES:
                plan_errors.append(f"{order_id}: 허용되지 않은 Terminal State입니다.")
            if state == "FILLED_SIMULATED":
                price = fill_prices.get(order_id)
                if not isinstance(price, (int, float)) or price <= 0:
                    plan_errors.append(f"{order_id}: 모의 체결 가격이 필요합니다.")
            elif order_id in fill_prices:
                plan_errors.append(f"{order_id}: 취소 주문에는 체결 가격을 넣을 수 없습니다.")
    lifecycles: tuple[SandboxOrderLifecycle, ...] = ()
    batch: SandboxOrderLifecycleBatch | None = None
    transition_errors: list[str] = []
    hash_ok = False
    preliminary_errors = (
        policy_errors + input_errors + source_errors
        + dispatch_errors + plan_errors
    )
    if not preliminary_errors and source_batch:
        receipt_map = {
            item.client_order_id: item for item in source_batch.receipts
        }
        values: list[SandboxOrderLifecycle] = []
        for request in source_batch.requests:
            receipt = receipt_map.get(request.client_order_id)
            if not receipt:
                transition_errors.append(
                    f"{request.client_order_id}: Dispatch Receipt가 없습니다."
                )
                continue
            values.append(
                build_lifecycle(
                    request,
                    receipt,
                    terminal_states[request.client_order_id],
                    fill_prices.get(request.client_order_id),
                    created_at,
                )
            )
        lifecycles = tuple(values)
    if not preliminary_errors and not transition_errors and source_batch:
        draft = SandboxOrderLifecycleBatch(
            lifecycle_batch_id=str(uuid.uuid4()),
            created_at=created_at,
            lifecycle_status="TRACKED_IN_MEMORY",
            dispatcher_result_id=source.dispatcher_result_id,
            dispatch_batch_id=source_batch.dispatch_batch_id,
            dispatch_batch_hash=source_batch.batch_hash,
            session_id=source_batch.session_id,
            operator=clean_operator,
            order_count=len(lifecycles),
            filled_count=sum(
                item.terminal_state == "FILLED_SIMULATED"
                for item in lifecycles
            ),
            cancelled_count=sum(
                item.terminal_state == "CANCELLED_SIMULATED"
                for item in lifecycles
            ),
            lifecycles=lifecycles,
            credentials_used=False,
            dns_lookup_performed=False,
            socket_created=False,
            http_request_sent=False,
            network_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_execution_authorized=False,
            batch_hash="",
        )
        batch = SandboxOrderLifecycleBatch(
            **{
                **asdict(draft),
                "lifecycles": draft.lifecycles,
                "batch_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
        hash_ok, transition_errors = verify_lifecycle_batch(batch)
    all_errors = preliminary_errors + transition_errors
    passed = bool(batch) and hash_ok and not all_errors
    status = "TRACKED_IN_MEMORY" if passed else (
        "BLOCKED" if not source_errors else "FAILED"
    )
    return SandboxOrderLifecycleTrackerResult(
        version="V14.2",
        created_at=created_at,
        tracker_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "TRACKED_IN_MEMORY": "Sandbox Order Lifecycle 추적 완료",
            "BLOCKED": "Lifecycle 입력 또는 전이 차단",
            "FAILED": "V14.1 Source 검증 실패",
        }[status],
        lifecycle_batch_id=batch.lifecycle_batch_id if batch else None,
        batch_hash=batch.batch_hash if batch else None,
        order_count=len(lifecycles),
        filled_count=batch.filled_count if batch else 0,
        cancelled_count=batch.cancelled_count if batch else 0,
        event_count=sum(item.event_count for item in lifecycles),
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        source_checks_passed=not source_errors,
        dispatch_checks_passed=not dispatch_errors,
        plan_checks_passed=not plan_errors,
        transition_checks_passed=bool(lifecycles) and not transition_errors,
        event_hash_checks_passed=hash_ok,
        lifecycle_hash_checks_passed=hash_ok,
        batch_hash_checks_passed=hash_ok,
        safety_checks_passed=not policy_errors,
        all_checks_passed=passed,
        lifecycle_tracking_completed=passed,
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
        lifecycle_policy=policy,
        batch=batch,
        reasons=[
            "Sandbox 주문 상태를 In-Memory Event Chain으로 추적했습니다."
            if passed else "Sandbox Order Lifecycle 추적이 차단되었습니다."
        ],
        warnings=all_errors + [
            "모든 상태와 체결은 Simulation이며 실제 Broker Event가 아닙니다."
        ],
        next_actions=[
            "Event, Lifecycle 및 Batch Hash를 수동 확인합니다.",
            "실제 Broker 체결 또는 계좌 정보로 해석하지 않습니다.",
        ],
    )


def save_lifecycle_result(
    result: SandboxOrderLifecycleTrackerResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"sandbox_order_lifecycle_{stamp}.json"
    latest = directory / "latest_sandbox_order_lifecycle.json"
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


def load_lifecycle_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V14.2":
        raise ValueError("V14.2 결과 파일이 아닙니다.")
    raw = payload.get("batch")
    if raw:
        lifecycles = []
        for item in raw.get("lifecycles", []):
            lifecycles.append(
                SandboxOrderLifecycle(
                    **{
                        **item,
                        "events": tuple(
                            SandboxOrderLifecycleEvent(**event)
                            for event in item.get("events", [])
                        ),
                    }
                )
            )
        batch = SandboxOrderLifecycleBatch(
            **{**raw, "lifecycles": tuple(lifecycles)}
        )
        valid, errors = verify_lifecycle_batch(batch)
        if not valid:
            raise ValueError("저장된 Lifecycle Batch가 올바르지 않습니다: " + "; ".join(errors))
    return payload
