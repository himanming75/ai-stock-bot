import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_broker_sandbox_adapter import (
    PaperBrokerSandboxAdapterResult,
    verify_handshake,
    verify_response,
)
from backtest.paper_order_translation_validator import (
    PaperOrderTranslationResult,
    TranslatedPaperOrder,
    verify_translation_batch,
)
from backtest.paper_submission_final_control import (
    PaperSubmissionFinalControlResult,
    verify_control_seal,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "sandbox_paper_order_dispatcher"
)
REQUIRED_DISPATCH_TEXT = "DISPATCH ORDERS TO IN MEMORY PAPER SANDBOX"


@dataclass(frozen=True)
class SandboxPaperOrderDispatcherPolicy:
    required_adapter_version: str = "V14.0"
    required_adapter_status: str = "SANDBOX_READY"
    required_control_version: str = "V13.9"
    required_translation_version: str = "V13.4"
    required_confirmation_text: str = REQUIRED_DISPATCH_TEXT
    dispatch_mode: str = "IN_MEMORY_ONLY"
    maximum_order_count: int = 20
    require_same_operator: bool = True
    require_exact_source_links: bool = True
    require_unique_order_ids: bool = True
    require_transmit_false: bool = True
    credentials_forbidden: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxDispatchRequest:
    dispatch_request_id: str
    created_at: str
    session_id: str
    control_id: str
    translation_batch_id: str
    client_order_id: str
    instrument: str
    side: str
    order_kind: str
    quantity: int
    price: float | None
    time_in_force: str
    dispatch_target: str
    credentials_included: bool
    transmit: bool
    request_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("request_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxDispatchReceipt:
    dispatch_receipt_id: str
    created_at: str
    request_id: str
    request_hash: str
    session_id: str
    client_order_id: str
    dispatch_status: str
    sandbox_queue_id: str
    broker_order_id: str | None
    sandbox_dispatch_recorded: bool
    broker_accepted: bool
    submitted: bool
    credentials_used: bool
    dns_lookup_performed: bool
    socket_created: bool
    http_request_sent: bool
    network_accessed: bool
    broker_api_called: bool
    live_execution_authorized: bool
    receipt_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("receipt_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SandboxDispatchBatch:
    dispatch_batch_id: str
    created_at: str
    dispatch_status: str
    adapter_result_id: str
    session_id: str
    control_result_id: str
    control_id: str
    translation_result_id: str
    translation_batch_id: str
    operator: str
    request_count: int
    receipt_count: int
    requests: tuple[SandboxDispatchRequest, ...]
    receipts: tuple[SandboxDispatchReceipt, ...]
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    batch_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["requests"] = [item.to_dict() for item in self.requests]
        payload["receipts"] = [item.to_dict() for item in self.receipts]
        payload.pop("batch_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["requests"] = [item.to_dict() for item in self.requests]
        payload["receipts"] = [item.to_dict() for item in self.receipts]
        return payload


@dataclass
class SandboxPaperOrderDispatcherResult:
    version: str
    created_at: str
    dispatcher_result_id: str
    result_status: str
    result_status_label: str
    dispatch_batch_id: str | None
    batch_hash: str | None
    request_count: int
    receipt_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    adapter_checks_passed: bool
    control_checks_passed: bool
    translation_checks_passed: bool
    linkage_checks_passed: bool
    mapping_checks_passed: bool
    receipt_checks_passed: bool
    batch_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    sandbox_dispatch_completed: bool
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
    dispatcher_policy: SandboxPaperOrderDispatcherPolicy
    batch: SandboxDispatchBatch | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["dispatcher_policy"] = self.dispatcher_policy.to_dict()
        payload["batch"] = self.batch.to_dict() if self.batch else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: SandboxPaperOrderDispatcherPolicy) -> list[str]:
    if not isinstance(policy, SandboxPaperOrderDispatcherPolicy):
        return ["Dispatcher Policy 형식이 올바르지 않습니다."]
    errors: list[str] = []
    expected = {
        "required_adapter_version": "V14.0",
        "required_adapter_status": "SANDBOX_READY",
        "required_control_version": "V13.9",
        "required_translation_version": "V13.4",
        "required_confirmation_text": REQUIRED_DISPATCH_TEXT,
        "dispatch_mode": "IN_MEMORY_ONLY",
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V14.1 기준과 다릅니다.")
    if policy.maximum_order_count <= 0:
        errors.append("Maximum Order Count가 올바르지 않습니다.")
    for name in (
        "require_same_operator",
        "require_exact_source_links",
        "require_unique_order_ids",
        "require_transmit_false",
        "credentials_forbidden",
        "network_access_disabled",
        "broker_api_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V14.1에서 True여야 합니다.")
    return errors


def validate_sources(
    adapter: Any,
    control_result: Any,
    translation: Any,
    checked_at: datetime,
) -> tuple[Any, Any, Any, Any, list[str], list[str], list[str]]:
    adapter_errors: list[str] = []
    control_errors: list[str] = []
    translation_errors: list[str] = []
    handshake = response = control = batch = None
    if not isinstance(adapter, PaperBrokerSandboxAdapterResult):
        adapter_errors.append("V14.0 Sandbox Adapter Result가 아닙니다.")
    elif not (
        adapter.version == "V14.0"
        and adapter.result_status == "SANDBOX_READY"
        and adapter.all_checks_passed
        and adapter.sandbox_session_ready
        and adapter.handshakes
        and adapter.responses
    ):
        adapter_errors.append("정상 V14.0 Sandbox Adapter Source가 아닙니다.")
    else:
        handshake = adapter.handshakes[-1]
        response = adapter.responses[-1]
        valid, errors = verify_handshake(handshake)
        if not valid:
            adapter_errors.extend(errors)
        valid, time_valid, errors = verify_response(response, checked_at)
        if not valid or not time_valid:
            adapter_errors.extend(errors)
        if (
            response.handshake_id != handshake.handshake_id
            or response.handshake_hash != handshake.handshake_hash
            or response.session_id != adapter.latest_session_id
        ):
            adapter_errors.append("V14.0 Handshake와 Response 연결이 다릅니다.")
    if not isinstance(control_result, PaperSubmissionFinalControlResult):
        control_errors.append("V13.9 Final Control Result가 아닙니다.")
    elif not (
        control_result.version == "V13.9"
        and control_result.result_status == "FINAL_CONTROL_PASSED"
        and control_result.all_checks_passed
        and control_result.controls
    ):
        control_errors.append("정상 V13.9 Final Control Source가 아닙니다.")
    else:
        control = control_result.controls[-1]
        valid, errors = verify_control_seal(control)
        if not valid:
            control_errors.extend(errors)
    if not isinstance(translation, PaperOrderTranslationResult):
        translation_errors.append("V13.4 Translation Result가 아닙니다.")
    elif not (
        translation.version == "V13.4"
        and translation.result_status == "VALIDATED"
        and translation.all_checks_passed
        and translation.translation_validated
        and translation.batch is not None
    ):
        translation_errors.append("정상 V13.4 Translation Source가 아닙니다.")
    else:
        batch = translation.batch
        valid, errors = verify_translation_batch(batch)
        if not valid:
            translation_errors.extend(errors)
    return (
        handshake, response, control, batch,
        adapter_errors, control_errors, translation_errors,
    )


def map_request(
    order: TranslatedPaperOrder,
    session_id: str,
    control_id: str,
    translation_batch_id: str,
    created_at: str,
) -> SandboxDispatchRequest:
    draft = SandboxDispatchRequest(
        dispatch_request_id=str(uuid.uuid4()),
        created_at=created_at,
        session_id=session_id,
        control_id=control_id,
        translation_batch_id=translation_batch_id,
        client_order_id=order.client_order_id,
        instrument=order.instrument,
        side=order.side,
        order_kind=order.order_kind,
        quantity=order.quantity,
        price=order.price,
        time_in_force=order.time_in_force,
        dispatch_target="memory://paper-sandbox/dispatch",
        credentials_included=False,
        transmit=False,
        request_hash="",
    )
    return SandboxDispatchRequest(
        **{
            **asdict(draft),
            "request_hash": sha256_payload(draft.payload_without_hash()),
        }
    )


def make_receipt(
    request: SandboxDispatchRequest,
    created_at: str,
) -> SandboxDispatchReceipt:
    draft = SandboxDispatchReceipt(
        dispatch_receipt_id=str(uuid.uuid4()),
        created_at=created_at,
        request_id=request.dispatch_request_id,
        request_hash=request.request_hash,
        session_id=request.session_id,
        client_order_id=request.client_order_id,
        dispatch_status="QUEUED_IN_MEMORY",
        sandbox_queue_id=str(uuid.uuid4()),
        broker_order_id=None,
        sandbox_dispatch_recorded=True,
        broker_accepted=False,
        submitted=False,
        credentials_used=False,
        dns_lookup_performed=False,
        socket_created=False,
        http_request_sent=False,
        network_accessed=False,
        broker_api_called=False,
        live_execution_authorized=False,
        receipt_hash="",
    )
    return SandboxDispatchReceipt(
        **{
            **asdict(draft),
            "receipt_hash": sha256_payload(draft.payload_without_hash()),
        }
    )


def verify_dispatch_batch(
    batch: SandboxDispatchBatch,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if batch.dispatch_status != "DISPATCHED_IN_MEMORY":
        errors.append("Dispatch Batch 상태가 올바르지 않습니다.")
    if not (
        batch.request_count == batch.receipt_count
        == len(batch.requests) == len(batch.receipts)
    ) or not batch.requests:
        errors.append("Dispatch Request와 Receipt 수가 다릅니다.")
    request_map = {item.dispatch_request_id: item for item in batch.requests}
    if len(request_map) != len(batch.requests):
        errors.append("중복 Dispatch Request ID가 있습니다.")
    for request in batch.requests:
        if request.credentials_included or request.transmit:
            errors.append(f"{request.client_order_id}: 위험한 Request입니다.")
        if request.request_hash != sha256_payload(request.payload_without_hash()):
            errors.append(f"{request.client_order_id}: Request Hash가 다릅니다.")
    for receipt in batch.receipts:
        request = request_map.get(receipt.request_id)
        if not request:
            errors.append(f"{receipt.client_order_id}: 연결 Request가 없습니다.")
            continue
        if (
            receipt.request_hash != request.request_hash
            or receipt.session_id != request.session_id
            or receipt.client_order_id != request.client_order_id
        ):
            errors.append(f"{receipt.client_order_id}: Receipt 연결이 다릅니다.")
        if not (
            receipt.dispatch_status == "QUEUED_IN_MEMORY"
            and receipt.sandbox_dispatch_recorded
            and receipt.broker_order_id is None
            and not receipt.broker_accepted
            and not receipt.submitted
        ):
            errors.append(f"{receipt.client_order_id}: Receipt 상태가 안전하지 않습니다.")
        if any((
            receipt.credentials_used,
            receipt.dns_lookup_performed,
            receipt.socket_created,
            receipt.http_request_sent,
            receipt.network_accessed,
            receipt.broker_api_called,
            receipt.live_execution_authorized,
        )):
            errors.append(f"{receipt.client_order_id}: 외부 실행 흔적이 있습니다.")
        if receipt.receipt_hash != sha256_payload(receipt.payload_without_hash()):
            errors.append(f"{receipt.client_order_id}: Receipt Hash가 다릅니다.")
    if any((
        batch.network_accessed,
        batch.broker_api_called,
        batch.broker_order_created,
        batch.order_submitted,
        batch.live_execution_authorized,
    )):
        errors.append("Dispatch Batch에 실제 실행 흔적이 있습니다.")
    if batch.batch_hash != sha256_payload(batch.payload_without_hash()):
        errors.append("Dispatch Batch Hash가 일치하지 않습니다.")
    return not errors, errors


def dispatch_sandbox_paper_orders(
    adapter: PaperBrokerSandboxAdapterResult,
    control_result: PaperSubmissionFinalControlResult,
    translation: PaperOrderTranslationResult,
    operator: str,
    confirmation_text: str,
    policy: SandboxPaperOrderDispatcherPolicy | None = None,
    now: datetime | None = None,
) -> SandboxPaperOrderDispatcherResult:
    policy = policy or SandboxPaperOrderDispatcherPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("Dispatch 확인 문구가 일치하지 않습니다.")
    (
        handshake, response, control, translation_batch,
        adapter_errors, control_errors, translation_errors,
    ) = validate_sources(adapter, control_result, translation, now)
    linkage_errors: list[str] = []
    mapping_errors: list[str] = []
    if handshake and response and control and translation_batch:
        if not (
            handshake.control_result_id == control_result.control_result_id
            and handshake.control_id == control.control_id
            and handshake.control_hash == control.control_hash
            and control.translation_batch_id == translation_batch.translation_batch_id
            and handshake.item_count == translation_batch.order_count
            and response.handshake_id == handshake.handshake_id
        ):
            linkage_errors.append("V13.4, V13.9, V14.0 Source 연결이 다릅니다.")
        if not (
            handshake.operator == control.operator
            == translation_batch.operator == clean_operator
        ):
            linkage_errors.append("Source와 Dispatch Operator가 일치하지 않습니다.")
        if len(translation_batch.orders) > policy.maximum_order_count:
            mapping_errors.append("Dispatch 허용 주문 수를 초과했습니다.")
        ids = [order.client_order_id for order in translation_batch.orders]
        if len(ids) != len(set(ids)):
            mapping_errors.append("중복 Client Order ID가 있습니다.")
        if any(order.transmit for order in translation_batch.orders):
            mapping_errors.append("Transmit=True 주문은 Dispatch할 수 없습니다.")
    requests: tuple[SandboxDispatchRequest, ...] = ()
    receipts: tuple[SandboxDispatchReceipt, ...] = ()
    batch: SandboxDispatchBatch | None = None
    receipt_errors: list[str] = []
    hash_ok = False
    source_errors = adapter_errors + control_errors + translation_errors
    preliminary_errors = (
        policy_errors + input_errors + source_errors
        + linkage_errors + mapping_errors
    )
    if (
        not preliminary_errors and translation_batch
        and response and control
    ):
        requests = tuple(
            map_request(
                order,
                response.session_id,
                control.control_id,
                translation_batch.translation_batch_id,
                created_at,
            )
            for order in translation_batch.orders
        )
        receipts = tuple(make_receipt(item, created_at) for item in requests)
        draft = SandboxDispatchBatch(
            dispatch_batch_id=str(uuid.uuid4()),
            created_at=created_at,
            dispatch_status="DISPATCHED_IN_MEMORY",
            adapter_result_id=adapter.adapter_result_id,
            session_id=response.session_id,
            control_result_id=control_result.control_result_id,
            control_id=control.control_id,
            translation_result_id=translation.translation_result_id,
            translation_batch_id=translation_batch.translation_batch_id,
            operator=clean_operator,
            request_count=len(requests),
            receipt_count=len(receipts),
            requests=requests,
            receipts=receipts,
            network_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_execution_authorized=False,
            batch_hash="",
        )
        batch = SandboxDispatchBatch(
            **{
                **asdict(draft),
                "requests": draft.requests,
                "receipts": draft.receipts,
                "batch_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
        hash_ok, receipt_errors = verify_dispatch_batch(batch)
    all_errors = preliminary_errors + receipt_errors
    passed = bool(batch) and hash_ok and not all_errors
    sources_valid = not source_errors
    status = "DISPATCHED_IN_MEMORY" if passed else (
        "BLOCKED" if sources_valid else "FAILED"
    )
    return SandboxPaperOrderDispatcherResult(
        version="V14.1",
        created_at=created_at,
        dispatcher_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "DISPATCHED_IN_MEMORY": "Sandbox Paper Order 메모리 Dispatch 완료",
            "BLOCKED": "Sandbox Dispatch 연결 또는 입력 차단",
            "FAILED": "Source 검증 실패",
        }[status],
        dispatch_batch_id=batch.dispatch_batch_id if batch else None,
        batch_hash=batch.batch_hash if batch else None,
        request_count=len(requests),
        receipt_count=len(receipts),
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        adapter_checks_passed=not adapter_errors,
        control_checks_passed=not control_errors,
        translation_checks_passed=not translation_errors,
        linkage_checks_passed=not linkage_errors,
        mapping_checks_passed=not mapping_errors,
        receipt_checks_passed=bool(receipts) and not receipt_errors,
        batch_hash_checks_passed=hash_ok,
        safety_checks_passed=not policy_errors,
        all_checks_passed=passed,
        sandbox_dispatch_completed=passed,
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
        dispatcher_policy=policy,
        batch=batch,
        reasons=[
            "Paper Order를 In-Memory Sandbox Queue에 기록했습니다."
            if passed else "Sandbox Paper Order Dispatch가 차단되었습니다."
        ],
        warnings=all_errors + [
            "QUEUED_IN_MEMORY는 실제 Broker 주문 제출 또는 접수가 아닙니다."
        ],
        next_actions=[
            "Request, Receipt 및 Batch Hash를 수동 확인합니다.",
            "실제 API Key, 계좌 또는 Broker Endpoint를 입력하지 않습니다.",
        ],
    )


def save_dispatch_result(
    result: SandboxPaperOrderDispatcherResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"sandbox_paper_order_dispatch_{stamp}.json"
    latest = directory / "latest_sandbox_paper_order_dispatch.json"
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


def load_dispatch_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V14.1":
        raise ValueError("V14.1 결과 파일이 아닙니다.")
    raw = payload.get("batch")
    if raw:
        batch = SandboxDispatchBatch(
            **{
                **raw,
                "requests": tuple(
                    SandboxDispatchRequest(**item)
                    for item in raw.get("requests", [])
                ),
                "receipts": tuple(
                    SandboxDispatchReceipt(**item)
                    for item in raw.get("receipts", [])
                ),
            }
        )
        valid, errors = verify_dispatch_batch(batch)
        if not valid:
            raise ValueError("저장된 Dispatch Batch가 올바르지 않습니다: " + "; ".join(errors))
    return payload
