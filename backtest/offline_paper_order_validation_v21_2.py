import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_order_model_v21_1 import (
    OfflinePaperOrderV211,
    OfflinePaperOrderV211Policy,
    OfflinePaperOrderV211Result,
    validate_policy as validate_order_policy,
    verify_offline_paper_order,
)
from backtest.offline_paper_trading_account_v21_0 import canonical_json


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "offline_paper_order_validation_v21_2"
)
REQUIRED_VALIDATION_TEXT = "VALIDATE OFFLINE PAPER ORDER DRAFT V21.2"


@dataclass(frozen=True)
class OfflinePaperOrderValidationV212Policy:
    required_source_version: str = "V21.1"
    required_source_status: str = "DRAFTED_IN_MEMORY"
    required_order_mode: str = "OFFLINE_PAPER_DRAFT"
    required_order_status: str = "DRAFTED_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_VALIDATION_TEXT
    validation_scope: str = "OFFLINE_PAPER_ONLY"
    require_same_operator: bool = True
    require_source_unchanged: bool = True
    require_order_hash: bool = True
    require_account_hash_linkage: bool = True
    require_result_order_linkage: bool = True
    require_notional_recalculation: bool = True
    require_resource_check: bool = True
    validation_only: bool = True
    source_mutation_disabled: bool = True
    funds_reservation_disabled: bool = True
    holdings_reservation_disabled: bool = True
    order_execution_disabled: bool = True
    automatic_execution_disabled: bool = True
    credentials_forbidden: bool = True
    market_data_api_disabled: bool = True
    account_api_disabled: bool = True
    network_access_disabled: bool = True
    broker_api_disabled: bool = True
    broker_order_creation_disabled: bool = True
    order_submission_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OfflinePaperOrderValidationCertificateV212:
    certificate_id: str
    created_at: str
    certificate_status: str
    validation_scope: str
    source_v21_1_result_id: str
    source_paper_order_id: str
    source_order_hash: str
    source_account_id: str
    source_account_hash: str
    operator: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    estimated_notional: float
    order_hash_valid: bool
    account_linkage_valid: bool
    result_order_linkage_valid: bool
    notional_recalculation_valid: bool
    resource_check_valid: bool
    source_unchanged: bool
    validation_checks: tuple[str, ...]
    funds_reserved: bool
    holdings_reserved: bool
    order_execution_authorized: bool
    automatic_execution_authorized: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    certificate_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("certificate_hash", None)
        payload["validation_checks"] = list(self.validation_checks)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self.payload_without_hash()
        payload["certificate_hash"] = self.certificate_hash
        return payload


@dataclass
class OfflinePaperOrderValidationV212Result:
    version: str
    created_at: str
    validation_result_id: str
    result_status: str
    result_status_label: str
    source_v21_1_result_id: str | None
    source_paper_order_id: str | None
    source_order_hash: str | None
    source_account_id: str | None
    source_account_hash: str | None
    certificate_id: str | None
    certificate_hash: str | None
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    order_hash_checks_passed: bool
    account_linkage_checks_passed: bool
    result_order_linkage_checks_passed: bool
    notional_checks_passed: bool
    resource_checks_passed: bool
    chronology_checks_passed: bool
    source_unchanged_checks_passed: bool
    certificate_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    order_validated: bool
    validation_certificate_created: bool
    funds_reserved: bool
    holdings_reserved: bool
    paper_order_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_order_created: bool
    live_execution_authorized: bool
    validation_policy: OfflinePaperOrderValidationV212Policy
    certificate: OfflinePaperOrderValidationCertificateV212 | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["validation_policy"] = self.validation_policy.to_dict()
        payload["certificate"] = (
            self.certificate.to_dict() if self.certificate else None
        )
        return payload


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def validate_policy(
    policy: OfflinePaperOrderValidationV212Policy,
) -> list[str]:
    if not isinstance(policy, OfflinePaperOrderValidationV212Policy):
        return ["Offline Paper Order Validation Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V21.1",
        "required_source_status": "DRAFTED_IN_MEMORY",
        "required_order_mode": "OFFLINE_PAPER_DRAFT",
        "required_order_status": "DRAFTED_IN_MEMORY",
        "required_confirmation_text": REQUIRED_VALIDATION_TEXT,
        "validation_scope": "OFFLINE_PAPER_ONLY",
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V21.2 기준과 다릅니다.")
    for name in (
        "require_same_operator",
        "require_source_unchanged",
        "require_order_hash",
        "require_account_hash_linkage",
        "require_result_order_linkage",
        "require_notional_recalculation",
        "require_resource_check",
        "validation_only",
        "source_mutation_disabled",
        "funds_reservation_disabled",
        "holdings_reservation_disabled",
        "order_execution_disabled",
        "automatic_execution_disabled",
        "credentials_forbidden",
        "market_data_api_disabled",
        "account_api_disabled",
        "network_access_disabled",
        "broker_api_disabled",
        "broker_order_creation_disabled",
        "order_submission_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(f"{name}는 V21.2에서 True여야 합니다.")
    return errors


def _safe_source(source: OfflinePaperOrderV211Result) -> bool:
    return not any(
        (
            source.funds_reserved,
            source.holdings_reserved,
            source.paper_order_execution_authorized,
            source.automatic_execution_authorized,
            not source.execution_blocked,
            source.transmit,
            source.credentials_used,
            source.market_data_api_called,
            source.account_api_called,
            source.network_accessed,
            source.broker_api_called,
            source.broker_order_created,
            source.order_submitted,
            source.live_order_created,
            source.live_execution_authorized,
        )
    )


def _result_order_linkage(
    source: OfflinePaperOrderV211Result,
    order: OfflinePaperOrderV211,
) -> bool:
    return all(
        (
            source.paper_order_id == order.paper_order_id,
            source.order_hash == order.order_hash,
            source.source_account_id == order.account_id,
            source.source_account_hash == order.account_hash,
            source.symbol == order.symbol,
            source.side == order.side,
            source.order_type == order.order_type,
            source.quantity == order.quantity,
            source.estimated_notional == order.estimated_notional,
        )
    )


def _resource_check(order: OfflinePaperOrderV211) -> bool:
    if order.side == "BUY":
        return order.estimated_notional <= order.cash_balance_snapshot
    if order.side == "SELL":
        return order.quantity <= order.position_quantity_snapshot
    return False


def verify_validation_certificate(
    certificate: OfflinePaperOrderValidationCertificateV212,
) -> tuple[bool, list[str]]:
    if not isinstance(
        certificate,
        OfflinePaperOrderValidationCertificateV212,
    ):
        return False, ["V21.2 Validation Certificate 형식 오류입니다."]
    errors: list[str] = []
    if certificate.certificate_status != "VALIDATED_IN_MEMORY":
        errors.append("Certificate Status가 올바르지 않습니다.")
    if certificate.validation_scope != "OFFLINE_PAPER_ONLY":
        errors.append("Validation Scope가 올바르지 않습니다.")
    if not all(
        (
            certificate.order_hash_valid,
            certificate.account_linkage_valid,
            certificate.result_order_linkage_valid,
            certificate.notional_recalculation_valid,
            certificate.resource_check_valid,
            certificate.source_unchanged,
            len(certificate.validation_checks) == 6,
            not certificate.funds_reserved,
            not certificate.holdings_reserved,
            not certificate.order_execution_authorized,
            not certificate.automatic_execution_authorized,
            not certificate.transmit,
            not certificate.credentials_used,
            not certificate.market_data_api_called,
            not certificate.account_api_called,
            not certificate.network_accessed,
            not certificate.broker_api_called,
            not certificate.broker_order_created,
            not certificate.order_submitted,
            not certificate.live_order_created,
            not certificate.live_execution_authorized,
        )
    ):
        errors.append("Validation Certificate 검사 또는 안전장치 오류입니다.")
    if certificate.certificate_hash != sha256_payload(
        certificate.payload_without_hash()
    ):
        errors.append("Validation Certificate Hash가 일치하지 않습니다.")
    return not errors, errors


def _result(
    policy_value: OfflinePaperOrderValidationV212Policy,
    now: datetime,
    status: str,
    reasons: list[str],
    source_result: OfflinePaperOrderV211Result | None = None,
    certificate_value: (
        OfflinePaperOrderValidationCertificateV212 | None
    ) = None,
    **checks: bool,
) -> OfflinePaperOrderValidationV212Result:
    validated = (
        status == "VALIDATED_IN_MEMORY"
        and certificate_value is not None
    )
    return OfflinePaperOrderValidationV212Result(
        version="V21.2",
        created_at=now.isoformat(),
        validation_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=(
            "Offline Paper Order 검증 완료"
            if validated
            else "Offline Paper Order 검증 차단"
            if status == "BLOCKED"
            else "Offline Paper Order 검증 실패"
        ),
        source_v21_1_result_id=(
            source_result.order_result_id if source_result else None
        ),
        source_paper_order_id=(
            source_result.paper_order_id if source_result else None
        ),
        source_order_hash=source_result.order_hash if source_result else None,
        source_account_id=(
            source_result.source_account_id if source_result else None
        ),
        source_account_hash=(
            source_result.source_account_hash if source_result else None
        ),
        certificate_id=(
            certificate_value.certificate_id
            if certificate_value
            else None
        ),
        certificate_hash=(
            certificate_value.certificate_hash
            if certificate_value
            else None
        ),
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        order_hash_checks_passed=checks.get("order_hash", False),
        account_linkage_checks_passed=checks.get("account_linkage", False),
        result_order_linkage_checks_passed=checks.get(
            "result_linkage",
            False,
        ),
        notional_checks_passed=checks.get("notional", False),
        resource_checks_passed=checks.get("resource", False),
        chronology_checks_passed=checks.get("chronology", False),
        source_unchanged_checks_passed=checks.get("unchanged", False),
        certificate_hash_checks_passed=checks.get(
            "certificate_hash",
            False,
        ),
        safety_checks_passed=True,
        all_checks_passed=validated,
        order_validated=validated,
        validation_certificate_created=validated,
        funds_reserved=False,
        holdings_reserved=False,
        paper_order_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        transmit=False,
        credentials_used=False,
        market_data_api_called=False,
        account_api_called=False,
        network_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_order_created=False,
        live_execution_authorized=False,
        validation_policy=policy_value,
        certificate=certificate_value,
        reasons=reasons,
        warnings=[
            "V21.2 인증서는 Offline Paper Order 초안의 읽기 전용 검증 결과입니다.",
            "검증 완료는 주문 체결 또는 Broker 전송 승인을 의미하지 않습니다.",
            "Broker API, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "V21.3 Offline Paper Order Validation Ledger 단계에서 인증서를 기록합니다."
        ],
    )


def validate_offline_paper_order_v21_2(
    source: Any,
    operator: Any,
    confirmation_text: Any,
    policy: OfflinePaperOrderValidationV212Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperOrderValidationV212Result:
    policy = policy or OfflinePaperOrderValidationV212Policy()
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        now = datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    if policy_errors:
        safe_policy = (
            policy
            if isinstance(policy, OfflinePaperOrderValidationV212Policy)
            else OfflinePaperOrderValidationV212Policy()
        )
        return _result(safe_policy, now, "BLOCKED", policy_errors)
    if not isinstance(source, OfflinePaperOrderV211Result):
        return _result(
            policy,
            now,
            "FAILED",
            ["Source는 V21.1 Offline Paper Order Result여야 합니다."],
            policy=True,
        )

    source_before = canonical_json(source.to_dict())
    source_errors: list[str] = []
    order = source.order
    if source.version != policy.required_source_version:
        source_errors.append("V21.1 Source Version이 아닙니다.")
    if source.result_status != policy.required_source_status:
        source_errors.append("V21.1 Order Draft 완료 상태가 아닙니다.")
    if not source.all_checks_passed or not source.order_draft_created:
        source_errors.append("V21.1 Source 검사가 완료되지 않았습니다.")
    if not isinstance(source.order_policy, OfflinePaperOrderV211Policy):
        source_errors.append("V21.1 Order Policy가 없습니다.")
    elif validate_order_policy(source.order_policy):
        source_errors.append("V21.1 Order Policy 안전 검증 실패입니다.")
    if not _safe_source(source):
        source_errors.append("V21.1 Source 안전장치 검증 실패입니다.")
    if order is None:
        source_errors.append("V21.1 Order Draft가 없습니다.")
    else:
        valid_order, order_errors = verify_offline_paper_order(order)
        if not valid_order or order_errors:
            source_errors.append("V21.1 Order Hash 검증 실패입니다.")
        if order.order_mode != policy.required_order_mode:
            source_errors.append("V21.1 Order Mode가 올바르지 않습니다.")
        if order.order_status != policy.required_order_status:
            source_errors.append("V21.1 Order Status가 올바르지 않습니다.")
        if not _result_order_linkage(source, order):
            source_errors.append("V21.1 Result와 Order 연결 검증 실패입니다.")
        if order.account_id != source.source_account_id:
            source_errors.append("V21.0 Account ID 연결 검증 실패입니다.")
        if order.account_hash != source.source_account_hash:
            source_errors.append("V21.0 Account Hash 연결 검증 실패입니다.")
        if (
            order.estimated_notional
            != round(order.estimated_price * order.quantity, 2)
        ):
            source_errors.append("V21.1 예상 주문금액 재계산 실패입니다.")
        if not _resource_check(order):
            source_errors.append("V21.1 가상 자원 조건 검증 실패입니다.")
    if source_errors:
        return _result(
            policy,
            now,
            "FAILED",
            source_errors,
            source_result=source,
            policy=True,
        )

    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator는 비어 있지 않은 문자열이어야 합니다.")
    elif policy.require_same_operator and operator.strip() != order.operator:
        input_errors.append("Operator가 V21.1 Order와 일치하지 않습니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("V21.2 확인 문구가 일치하지 않습니다.")
    chronology_valid = False
    try:
        order_created_at = datetime.fromisoformat(order.created_at)
        chronology_valid = now >= order_created_at
        if not chronology_valid:
            input_errors.append("Validation 시간이 V21.1 Order보다 이전입니다.")
    except (TypeError, ValueError):
        input_errors.append("V21.1 Order 시간이 올바르지 않습니다.")
    if input_errors:
        return _result(
            policy,
            now,
            "BLOCKED",
            input_errors,
            source_result=source,
            policy=True,
            source=True,
            order_hash=True,
            account_linkage=True,
            result_linkage=True,
            notional=True,
            resource=True,
        )

    unchanged = source_before == canonical_json(source.to_dict())
    if not unchanged:
        return _result(
            policy,
            now,
            "FAILED",
            ["V21.2 검증 중 V21.1 Source가 변경되었습니다."],
            source_result=source,
            policy=True,
            input=True,
            source=True,
            order_hash=True,
            account_linkage=True,
            result_linkage=True,
            notional=True,
            resource=True,
            chronology=True,
        )

    validation_checks = (
        "ORDER_HASH_VALID",
        "ACCOUNT_LINKAGE_VALID",
        "RESULT_ORDER_LINKAGE_VALID",
        "NOTIONAL_RECALCULATION_VALID",
        "RESOURCE_CHECK_VALID",
        "SOURCE_UNCHANGED",
    )
    payload = {
        "certificate_id": str(uuid.uuid4()),
        "created_at": now.isoformat(),
        "certificate_status": "VALIDATED_IN_MEMORY",
        "validation_scope": "OFFLINE_PAPER_ONLY",
        "source_v21_1_result_id": source.order_result_id,
        "source_paper_order_id": order.paper_order_id,
        "source_order_hash": order.order_hash,
        "source_account_id": order.account_id,
        "source_account_hash": order.account_hash,
        "operator": operator.strip(),
        "symbol": order.symbol,
        "side": order.side,
        "order_type": order.order_type,
        "quantity": order.quantity,
        "estimated_notional": order.estimated_notional,
        "order_hash_valid": True,
        "account_linkage_valid": True,
        "result_order_linkage_valid": True,
        "notional_recalculation_valid": True,
        "resource_check_valid": True,
        "source_unchanged": True,
        "validation_checks": validation_checks,
        "funds_reserved": False,
        "holdings_reserved": False,
        "order_execution_authorized": False,
        "automatic_execution_authorized": False,
        "transmit": False,
        "credentials_used": False,
        "market_data_api_called": False,
        "account_api_called": False,
        "network_accessed": False,
        "broker_api_called": False,
        "broker_order_created": False,
        "order_submitted": False,
        "live_order_created": False,
        "live_execution_authorized": False,
    }
    hash_payload = dict(payload)
    hash_payload["validation_checks"] = list(validation_checks)
    certificate = OfflinePaperOrderValidationCertificateV212(
        **payload,
        certificate_hash=sha256_payload(hash_payload),
    )
    valid_certificate, certificate_errors = verify_validation_certificate(
        certificate
    )
    if not valid_certificate:
        return _result(
            policy,
            now,
            "FAILED",
            certificate_errors,
            source_result=source,
            policy=True,
            input=True,
            source=True,
            order_hash=True,
            account_linkage=True,
            result_linkage=True,
            notional=True,
            resource=True,
            chronology=True,
            unchanged=True,
        )
    return _result(
        policy,
        now,
        "VALIDATED_IN_MEMORY",
        [],
        source_result=source,
        certificate_value=certificate,
        policy=True,
        input=True,
        source=True,
        order_hash=True,
        account_linkage=True,
        result_linkage=True,
        notional=True,
        resource=True,
        chronology=True,
        unchanged=True,
        certificate_hash=True,
    )


def save_validation_result(
    result: OfflinePaperOrderValidationV212Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = result.created_at.replace(":", "-").replace("+", "_")
    report_path = output_directory / f"order_validation_{stamp}.json"
    latest_path = output_directory / "latest.json"
    text = json.dumps(
        result.to_dict(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    report_path.write_text(text, encoding="utf-8")
    latest_path.write_text(text, encoding="utf-8")
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return report_path, latest_path


def load_validation_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
