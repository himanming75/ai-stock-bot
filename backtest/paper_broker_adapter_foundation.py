import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.authorized_paper_run_execution_envelope import (
    AuthorizedPaperRunExecutionEnvelope,
    AuthorizedPaperRunExecutionEnvelopeResult,
    verify_execution_envelope,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine" / "paper_broker_adapter_foundation"
)
REQUIRED_ADAPTER_TEXT = "PREPARE PAPER BROKER ADAPTER"
VALID_ADAPTER_STATUSES = {"PREPARED", "BLOCKED", "FAILED"}


@dataclass(frozen=True)
class PaperBrokerAdapterPolicy:
    required_source_version: str = "V12.9"
    required_source_status: str = "SEALED"
    required_confirmation_text: str = REQUIRED_ADAPTER_TEXT
    adapter_name: str = "RESEARCH_PAPER_ADAPTER"
    adapter_mode: str = "DRY_RUN_ONLY"
    maximum_ticket_count: int = 20
    require_source_hash: bool = True
    require_same_operator: bool = True
    require_unique_client_order_ids: bool = True
    network_access_disabled: bool = True
    account_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperBrokerTicket:
    client_order_id: str
    symbol: str
    action: str
    order_type: str
    quantity: int
    limit_price: float | None
    time_in_force: str
    transmit: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperBrokerAdapterPackage:
    adapter_package_id: str
    created_at: str
    adapter_status: str
    adapter_name: str
    adapter_mode: str
    envelope_id: str
    envelope_hash: str
    authorization_id: str
    trading_date: str
    operator: str
    ticket_count: int
    tickets: tuple[PaperBrokerTicket, ...]
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    package_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tickets"] = [ticket.to_dict() for ticket in self.tickets]
        payload.pop("package_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["tickets"] = [ticket.to_dict() for ticket in self.tickets]
        return payload


@dataclass
class PaperBrokerAdapterResult:
    version: str
    created_at: str
    adapter_result_id: str
    result_status: str
    result_status_label: str
    adapter_package_id: str | None
    package_hash: str | None
    ticket_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    mapping_checks_passed: bool
    package_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    paper_adapter_prepared: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    network_accessed: bool
    account_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    adapter_policy: PaperBrokerAdapterPolicy
    adapter_package: PaperBrokerAdapterPackage | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["adapter_policy"] = self.adapter_policy.to_dict()
        payload["adapter_package"] = (
            self.adapter_package.to_dict()
            if self.adapter_package is not None
            else None
        )
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def calculate_package_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: PaperBrokerAdapterPolicy) -> list[str]:
    errors: list[str] = []
    if policy.required_source_version != "V12.9":
        errors.append("Source Version은 V12.9여야 합니다.")
    if policy.required_source_status != "SEALED":
        errors.append("Source Status는 SEALED여야 합니다.")
    if policy.adapter_mode != "DRY_RUN_ONLY":
        errors.append("Adapter Mode는 DRY_RUN_ONLY여야 합니다.")
    if policy.maximum_ticket_count < 1:
        errors.append("Maximum Ticket Count가 올바르지 않습니다.")
    safety = (
        policy.network_access_disabled
        and policy.account_access_disabled
        and policy.broker_api_disabled
        and policy.order_submission_disabled
        and policy.live_execution_disabled
    )
    if not safety:
        errors.append("모든 실행 차단 정책이 활성화되어야 합니다.")
    return errors


def validate_source(
    source: AuthorizedPaperRunExecutionEnvelopeResult,
    operator: str,
    policy: PaperBrokerAdapterPolicy,
) -> tuple[AuthorizedPaperRunExecutionEnvelope | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, AuthorizedPaperRunExecutionEnvelopeResult):
        return None, ["V12.9 Result 형식이 아닙니다."]
    if source.version != policy.required_source_version:
        errors.append("V12.9 Source가 아닙니다.")
    if source.result_status != policy.required_source_status:
        errors.append("SEALED Source가 아닙니다.")
    envelope = source.envelope
    if envelope is None:
        errors.append("Execution Envelope가 없습니다.")
        return None, errors
    valid, _, verify_errors = verify_execution_envelope(envelope)
    if not valid:
        errors.extend(verify_errors)
    if not source.all_checks_passed or not source.paper_envelope_authorized:
        errors.append("안전하게 승인된 Envelope가 아닙니다.")
    if source.paper_execution_authorized or source.broker_api_called:
        errors.append("실행 흔적이 있는 Source는 사용할 수 없습니다.")
    if policy.require_same_operator and envelope.operator != operator.strip():
        errors.append("Operator가 Source와 일치하지 않습니다.")
    return envelope, errors


def map_tickets(
    envelope: AuthorizedPaperRunExecutionEnvelope,
    policy: PaperBrokerAdapterPolicy,
) -> tuple[tuple[PaperBrokerTicket, ...], list[str]]:
    errors: list[str] = []
    tickets: list[PaperBrokerTicket] = []
    ids: set[str] = set()
    if not envelope.orders:
        errors.append("변환할 Paper Order가 없습니다.")
    if len(envelope.orders) > policy.maximum_ticket_count:
        errors.append("Ticket 허용 개수를 초과했습니다.")
    for order in envelope.orders:
        client_id = order.order_id.strip()
        if not client_id:
            errors.append("Client Order ID가 비어 있습니다.")
            continue
        if client_id in ids:
            errors.append("중복 Client Order ID가 있습니다.")
            continue
        ids.add(client_id)
        if order.side not in {"BUY", "SELL"}:
            errors.append(f"{client_id}: Action이 올바르지 않습니다.")
            continue
        if order.order_type not in {"MARKET", "LIMIT"}:
            errors.append(f"{client_id}: Order Type이 올바르지 않습니다.")
            continue
        if order.quantity <= 0:
            errors.append(f"{client_id}: Quantity가 올바르지 않습니다.")
            continue
        if order.order_type == "LIMIT" and (
            order.limit_price is None or order.limit_price <= 0
        ):
            errors.append(f"{client_id}: Limit Price가 올바르지 않습니다.")
            continue
        tickets.append(
            PaperBrokerTicket(
                client_order_id=client_id,
                symbol=order.symbol,
                action=order.side,
                order_type=order.order_type,
                quantity=order.quantity,
                limit_price=order.limit_price,
                time_in_force="DAY",
                transmit=False,
            )
        )
    return tuple(tickets), errors


def verify_adapter_package(
    package: PaperBrokerAdapterPackage,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if package.adapter_status != "PREPARED":
        errors.append("Adapter Package가 PREPARED 상태가 아닙니다.")
    if package.adapter_mode != "DRY_RUN_ONLY":
        errors.append("Adapter Mode가 안전하지 않습니다.")
    if package.ticket_count != len(package.tickets):
        errors.append("Ticket Count가 일치하지 않습니다.")
    if not package.tickets or any(ticket.transmit for ticket in package.tickets):
        errors.append("Ticket 전송 설정이 안전하지 않습니다.")
    if any(
        (
            package.network_accessed,
            package.account_accessed,
            package.broker_api_called,
            package.broker_order_created,
            package.order_submitted,
            package.live_order_created,
            package.live_execution_authorized,
        )
    ):
        errors.append("Adapter Package에 실행 흔적이 있습니다.")
    expected = calculate_package_hash(package.payload_without_hash())
    if package.package_hash != expected:
        errors.append("Adapter Package Hash가 일치하지 않습니다.")
    return not errors, errors


def build_paper_broker_adapter_package(
    source: AuthorizedPaperRunExecutionEnvelopeResult,
    operator: str,
    confirmation_text: str,
    policy: PaperBrokerAdapterPolicy | None = None,
    now: datetime | None = None,
) -> PaperBrokerAdapterResult:
    policy = policy or PaperBrokerAdapterPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    reasons: list[str] = []
    errors = validate_policy(policy)
    policy_ok = not errors
    input_errors: list[str] = []
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("확인 문구가 일치하지 않습니다.")
    input_ok = not input_errors
    envelope, source_errors = validate_source(source, clean_operator, policy)
    source_ok = not source_errors
    tickets: tuple[PaperBrokerTicket, ...] = ()
    mapping_errors: list[str] = []
    if envelope is not None and source_ok:
        tickets, mapping_errors = map_tickets(envelope, policy)
    mapping_ok = not mapping_errors and bool(tickets)
    all_errors = errors + input_errors + source_errors + mapping_errors
    package: PaperBrokerAdapterPackage | None = None
    hash_ok = False
    if not all_errors and envelope is not None:
        draft = PaperBrokerAdapterPackage(
            adapter_package_id=str(uuid.uuid4()),
            created_at=created_at,
            adapter_status="PREPARED",
            adapter_name=policy.adapter_name,
            adapter_mode=policy.adapter_mode,
            envelope_id=envelope.envelope_id,
            envelope_hash=envelope.envelope_hash,
            authorization_id=envelope.authorization_id,
            trading_date=envelope.trading_date,
            operator=clean_operator,
            ticket_count=len(tickets),
            tickets=tickets,
            network_accessed=False,
            account_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_order_created=False,
            live_execution_authorized=False,
            package_hash="",
        )
        package = PaperBrokerAdapterPackage(
            **{
                **asdict(draft),
                "tickets": draft.tickets,
                "package_hash": calculate_package_hash(draft.payload_without_hash()),
            }
        )
        hash_ok, hash_errors = verify_adapter_package(package)
        all_errors.extend(hash_errors)
    safety_ok = (
        policy.network_access_disabled
        and policy.account_access_disabled
        and policy.broker_api_disabled
        and policy.order_submission_disabled
        and policy.live_execution_disabled
    )
    passed = (
        policy_ok and input_ok and source_ok and mapping_ok
        and hash_ok and safety_ok and not all_errors
    )
    status = "PREPARED" if passed else ("BLOCKED" if source_ok else "FAILED")
    reasons.append(
        "Paper Broker Adapter Package가 준비되었습니다."
        if passed
        else "Paper Broker Adapter Package가 차단되었습니다."
    )
    return PaperBrokerAdapterResult(
        version="V13.0",
        created_at=created_at,
        adapter_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label={
            "PREPARED": "Paper Broker Adapter 준비 완료",
            "BLOCKED": "입력 또는 Mapping 차단",
            "FAILED": "Source 검증 실패",
        }[status],
        adapter_package_id=package.adapter_package_id if package else None,
        package_hash=package.package_hash if package else None,
        ticket_count=len(tickets),
        policy_checks_passed=policy_ok,
        input_checks_passed=input_ok,
        source_checks_passed=source_ok,
        mapping_checks_passed=mapping_ok,
        package_hash_checks_passed=hash_ok,
        safety_checks_passed=safety_ok,
        all_checks_passed=passed,
        paper_adapter_prepared=passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        network_accessed=False,
        account_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        adapter_policy=policy,
        adapter_package=package,
        reasons=reasons,
        warnings=all_errors + [
            "V13.0은 연결 규격만 준비하며 Broker에 접속하지 않습니다."
        ],
        next_actions=[
            "생성된 Ticket Mapping과 Hash를 수동 검토합니다.",
            "실제 계좌 정보나 API Key를 입력하지 않습니다.",
        ],
    )


def save_paper_broker_adapter_result(
    result: PaperBrokerAdapterResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"paper_broker_adapter_{stamp}.json"
    latest = directory / "latest_paper_broker_adapter.json"
    payload = result.to_dict()
    for path in (report, latest):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(path)
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_paper_broker_adapter_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V13.0":
        raise ValueError("V13.0 결과 파일이 아닙니다.")
    package = payload.get("adapter_package")
    if package is not None:
        saved_hash = package.get("package_hash")
        hash_payload = dict(package)
        hash_payload.pop("package_hash", None)
        if saved_hash != calculate_package_hash(hash_payload):
            raise ValueError("저장된 Adapter Package가 변조되었습니다.")
    return payload


def print_paper_broker_adapter_result(result: PaperBrokerAdapterResult) -> None:
    print("=" * 92)
    print("AI STOCK BOT V13.0 PAPER BROKER ADAPTER FOUNDATION")
    print("=" * 92)
    print(f"Status                  : {result.result_status}")
    print(f"Adapter prepared        : {result.paper_adapter_prepared}")
    print(f"Ticket count            : {result.ticket_count}")
    print(f"Network accessed        : {result.network_accessed}")
    print(f"Account accessed        : {result.account_accessed}")
    print(f"Broker API called       : {result.broker_api_called}")
    print(f"Order submitted         : {result.order_submitted}")
    print(f"Live execution          : {result.live_execution_authorized}")
    print("=" * 92)
