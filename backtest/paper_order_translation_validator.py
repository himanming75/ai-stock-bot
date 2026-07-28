import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_broker_adapter_foundation import (
    PaperBrokerAdapterPackage,
    PaperBrokerAdapterResult,
    PaperBrokerTicket,
    verify_adapter_package,
)
from backtest.paper_broker_capability_manifest import (
    PaperBrokerCapabilityManifest,
    PaperBrokerCapabilityManifestResult,
    verify_capability_manifest,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT / "output" / "trading_engine"
    / "paper_order_translation_validator"
)
REQUIRED_TRANSLATION_TEXT = "VALIDATE PAPER ORDER TRANSLATION"


@dataclass(frozen=True)
class PaperOrderTranslationPolicy:
    required_manifest_version: str = "V13.3"
    required_manifest_status: str = "DECLARED"
    required_adapter_version: str = "V13.0"
    required_adapter_status: str = "PREPARED"
    required_confirmation_text: str = REQUIRED_TRANSLATION_TEXT
    target_schema: str = "BROKER_NEUTRAL_V1"
    require_same_operator: bool = True
    require_same_broker_profile: bool = True
    require_unique_order_ids: bool = True
    require_transmit_false: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TranslatedPaperOrder:
    client_order_id: str
    instrument: str
    side: str
    order_kind: str
    quantity: int
    price: float | None
    time_in_force: str
    transmit: bool
    source_ticket_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperOrderTranslationBatch:
    translation_batch_id: str
    created_at: str
    translation_status: str
    target_schema: str
    manifest_id: str
    manifest_hash: str
    adapter_package_id: str
    adapter_package_hash: str
    broker_profile: str
    operator: str
    order_count: int
    orders: tuple[TranslatedPaperOrder, ...]
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    batch_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["orders"] = [order.to_dict() for order in self.orders]
        payload.pop("batch_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["orders"] = [order.to_dict() for order in self.orders]
        return payload


@dataclass
class PaperOrderTranslationResult:
    version: str
    created_at: str
    translation_result_id: str
    result_status: str
    result_status_label: str
    translation_batch_id: str | None
    batch_hash: str | None
    translated_order_count: int
    policy_checks_passed: bool
    input_checks_passed: bool
    manifest_checks_passed: bool
    adapter_checks_passed: bool
    cross_source_checks_passed: bool
    translation_checks_passed: bool
    batch_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    translation_validated: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    network_accessed: bool
    account_accessed: bool
    session_opened: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    translation_policy: PaperOrderTranslationPolicy
    batch: PaperOrderTranslationBatch | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["translation_policy"] = self.translation_policy.to_dict()
        payload["batch"] = self.batch.to_dict() if self.batch else None
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: PaperOrderTranslationPolicy) -> list[str]:
    errors: list[str] = []
    if policy.required_manifest_version != "V13.3":
        errors.append("Manifest Version은 V13.3이어야 합니다.")
    if policy.required_adapter_version != "V13.0":
        errors.append("Adapter Version은 V13.0이어야 합니다.")
    if policy.target_schema != "BROKER_NEUTRAL_V1":
        errors.append("Target Schema가 허용되지 않습니다.")
    if not (
        policy.require_transmit_false and policy.network_access_disabled
        and policy.broker_api_disabled and policy.order_submission_disabled
        and policy.live_execution_disabled
    ):
        errors.append("변환 및 실행 안전정책이 올바르지 않습니다.")
    return errors


def validate_manifest_source(
    source: PaperBrokerCapabilityManifestResult,
    policy: PaperOrderTranslationPolicy,
) -> tuple[PaperBrokerCapabilityManifest | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, PaperBrokerCapabilityManifestResult):
        return None, ["V13.3 Manifest Result 형식이 아닙니다."]
    if source.version != policy.required_manifest_version:
        errors.append("V13.3 Manifest Source가 아닙니다.")
    if source.result_status != policy.required_manifest_status:
        errors.append("DECLARED Manifest가 아닙니다.")
    manifest = source.manifest
    if manifest is None:
        errors.append("Capability Manifest가 없습니다.")
        return None, errors
    valid, verify_errors = verify_capability_manifest(manifest)
    if not valid:
        errors.extend(verify_errors)
    if not source.all_checks_passed or not source.capability_manifest_created:
        errors.append("검증된 Capability Manifest가 아닙니다.")
    return manifest, errors


def validate_adapter_source(
    source: PaperBrokerAdapterResult,
    policy: PaperOrderTranslationPolicy,
) -> tuple[PaperBrokerAdapterPackage | None, list[str]]:
    errors: list[str] = []
    if not isinstance(source, PaperBrokerAdapterResult):
        return None, ["V13.0 Adapter Result 형식이 아닙니다."]
    if source.version != policy.required_adapter_version:
        errors.append("V13.0 Adapter Source가 아닙니다.")
    if source.result_status != policy.required_adapter_status:
        errors.append("PREPARED Adapter가 아닙니다.")
    package = source.adapter_package
    if package is None:
        errors.append("Adapter Package가 없습니다.")
        return None, errors
    valid, verify_errors = verify_adapter_package(package)
    if not valid:
        errors.extend(verify_errors)
    if not source.all_checks_passed or not source.paper_adapter_prepared:
        errors.append("검증된 Adapter Package가 아닙니다.")
    return package, errors


def translate_tickets(
    tickets: tuple[PaperBrokerTicket, ...],
    manifest: PaperBrokerCapabilityManifest,
    policy: PaperOrderTranslationPolicy,
) -> tuple[tuple[TranslatedPaperOrder, ...], list[str]]:
    errors: list[str] = []
    translated: list[TranslatedPaperOrder] = []
    seen: set[str] = set()
    for ticket in tickets:
        if ticket.client_order_id in seen:
            errors.append("중복 Client Order ID가 있습니다.")
            continue
        seen.add(ticket.client_order_id)
        if ticket.order_type not in manifest.supported_order_types:
            errors.append(f"{ticket.client_order_id}: 지원하지 않는 Order Type입니다.")
            continue
        if ticket.action not in manifest.supported_actions:
            errors.append(f"{ticket.client_order_id}: 지원하지 않는 Action입니다.")
            continue
        if ticket.time_in_force not in manifest.supported_time_in_force:
            errors.append(f"{ticket.client_order_id}: 지원하지 않는 TIF입니다.")
            continue
        if ticket.quantity <= 0:
            errors.append(f"{ticket.client_order_id}: Quantity가 올바르지 않습니다.")
            continue
        if ticket.order_type == "LIMIT" and (
            ticket.limit_price is None or ticket.limit_price <= 0
        ):
            errors.append(f"{ticket.client_order_id}: Limit Price가 올바르지 않습니다.")
            continue
        if policy.require_transmit_false and ticket.transmit:
            errors.append(f"{ticket.client_order_id}: transmit=True가 차단되었습니다.")
            continue
        ticket_hash = sha256_payload(ticket.to_dict())
        translated.append(
            TranslatedPaperOrder(
                client_order_id=ticket.client_order_id,
                instrument=ticket.symbol,
                side=ticket.action,
                order_kind=ticket.order_type,
                quantity=ticket.quantity,
                price=ticket.limit_price,
                time_in_force=ticket.time_in_force,
                transmit=False,
                source_ticket_hash=ticket_hash,
            )
        )
    if not translated:
        errors.append("변환된 주문이 없습니다.")
    return tuple(translated), errors


def verify_translation_batch(
    batch: PaperOrderTranslationBatch,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if batch.translation_status != "VALIDATED":
        errors.append("Translation Batch가 VALIDATED 상태가 아닙니다.")
    if batch.order_count != len(batch.orders) or not batch.orders:
        errors.append("Order Count가 일치하지 않습니다.")
    if any(order.transmit for order in batch.orders):
        errors.append("transmit=True 주문이 있습니다.")
    if any(
        (
            batch.network_accessed, batch.broker_api_called,
            batch.broker_order_created, batch.order_submitted,
            batch.live_execution_authorized,
        )
    ):
        errors.append("Batch에 연결 또는 실행 흔적이 있습니다.")
    if batch.batch_hash != sha256_payload(batch.payload_without_hash()):
        errors.append("Translation Batch Hash가 일치하지 않습니다.")
    return not errors, errors


def validate_paper_order_translation(
    manifest_source: PaperBrokerCapabilityManifestResult,
    adapter_source: PaperBrokerAdapterResult,
    operator: str,
    confirmation_text: str,
    policy: PaperOrderTranslationPolicy | None = None,
    now: datetime | None = None,
) -> PaperOrderTranslationResult:
    policy = policy or PaperOrderTranslationPolicy()
    now = now or datetime.now().astimezone()
    created_at = now.isoformat()
    policy_errors = validate_policy(policy)
    clean_operator = operator.strip() if isinstance(operator, str) else ""
    input_errors: list[str] = []
    if not clean_operator:
        input_errors.append("Operator가 필요합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("확인 문구가 일치하지 않습니다.")
    manifest, manifest_errors = validate_manifest_source(manifest_source, policy)
    package, adapter_errors = validate_adapter_source(adapter_source, policy)
    cross_errors: list[str] = []
    if manifest and package:
        if policy.require_same_operator and not (
            manifest.operator == package.operator == clean_operator
        ):
            cross_errors.append("Operator 연결이 일치하지 않습니다.")
        compatible_profile = (
            manifest.broker_profile == "GENERIC_PAPER"
            and package.adapter_name == "RESEARCH_PAPER_ADAPTER"
            and package.adapter_mode == "DRY_RUN_ONLY"
        )
        if policy.require_same_broker_profile and not compatible_profile:
            cross_errors.append("Broker Profile과 Adapter 조합이 호환되지 않습니다.")
    orders: tuple[TranslatedPaperOrder, ...] = ()
    translation_errors: list[str] = []
    if manifest and package and not manifest_errors and not adapter_errors:
        orders, translation_errors = translate_tickets(
            package.tickets, manifest, policy
        )
    batch: PaperOrderTranslationBatch | None = None
    hash_ok = False
    all_errors = (
        policy_errors + input_errors + manifest_errors + adapter_errors
        + cross_errors + translation_errors
    )
    if not all_errors and manifest and package:
        draft = PaperOrderTranslationBatch(
            translation_batch_id=str(uuid.uuid4()),
            created_at=created_at,
            translation_status="VALIDATED",
            target_schema=policy.target_schema,
            manifest_id=manifest.manifest_id,
            manifest_hash=manifest.manifest_hash,
            adapter_package_id=package.adapter_package_id,
            adapter_package_hash=package.package_hash,
            broker_profile=manifest.broker_profile,
            operator=clean_operator,
            order_count=len(orders),
            orders=orders,
            network_accessed=False,
            broker_api_called=False,
            broker_order_created=False,
            order_submitted=False,
            live_execution_authorized=False,
            batch_hash="",
        )
        batch = PaperOrderTranslationBatch(
            **{
                **asdict(draft),
                "orders": draft.orders,
                "batch_hash": sha256_payload(draft.payload_without_hash()),
            }
        )
        hash_ok, hash_errors = verify_translation_batch(batch)
        all_errors.extend(hash_errors)
    source_ok = not manifest_errors and not adapter_errors
    safety_ok = (
        policy.require_transmit_false and policy.network_access_disabled
        and policy.broker_api_disabled and policy.order_submission_disabled
        and policy.live_execution_disabled
    )
    passed = (
        not policy_errors and not input_errors and source_ok
        and not cross_errors and not translation_errors and bool(orders)
        and hash_ok and safety_ok and not all_errors
    )
    status = "VALIDATED" if passed else ("BLOCKED" if source_ok else "FAILED")
    return PaperOrderTranslationResult(
        version="V13.4", created_at=created_at,
        translation_result_id=str(uuid.uuid4()), result_status=status,
        result_status_label={
            "VALIDATED": "Paper Order 변환 검증 완료",
            "BLOCKED": "변환 입력 또는 Mapping 차단",
            "FAILED": "Source 검증 실패",
        }[status],
        translation_batch_id=batch.translation_batch_id if batch else None,
        batch_hash=batch.batch_hash if batch else None,
        translated_order_count=len(orders),
        policy_checks_passed=not policy_errors,
        input_checks_passed=not input_errors,
        manifest_checks_passed=not manifest_errors,
        adapter_checks_passed=not adapter_errors,
        cross_source_checks_passed=not cross_errors,
        translation_checks_passed=bool(orders) and not translation_errors,
        batch_hash_checks_passed=hash_ok,
        safety_checks_passed=safety_ok,
        all_checks_passed=passed,
        translation_validated=passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        network_accessed=False, account_accessed=False, session_opened=False,
        broker_api_called=False, broker_order_created=False,
        order_submitted=False, live_order_created=False,
        live_execution_authorized=False,
        translation_policy=policy, batch=batch,
        reasons=[
            "Broker 중립형 Paper 주문 변환을 검증했습니다."
            if passed else "Paper 주문 변환이 차단되었습니다."
        ],
        warnings=all_errors + [
            "V13.4는 Payload만 검증하며 실제 주문을 제출하지 않습니다."
        ],
        next_actions=[
            "변환된 필드와 Source Ticket Hash를 수동 검토합니다.",
            "Broker API 또는 실제 계좌를 연결하지 않습니다.",
        ],
    )


def save_translation_result(
    result: PaperOrderTranslationResult,
    directory: Path | None = None,
) -> tuple[Path, Path]:
    directory = directory or OUTPUT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
    report = directory / f"paper_order_translation_{stamp}.json"
    latest = directory / "latest_paper_order_translation.json"
    payload = result.to_dict()
    for path in (report, latest):
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temp.replace(path)
    result.report_path = str(report)
    result.latest_path = str(latest)
    return report, latest


def load_translation_result(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != "V13.4":
        raise ValueError("V13.4 결과 파일이 아닙니다.")
    batch = payload.get("batch")
    if batch:
        saved_hash = batch.get("batch_hash")
        hash_payload = dict(batch)
        hash_payload.pop("batch_hash", None)
        if saved_hash != sha256_payload(hash_payload):
            raise ValueError("저장된 Translation Batch가 변조되었습니다.")
    return payload
