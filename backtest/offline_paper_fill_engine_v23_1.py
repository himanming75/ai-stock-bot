"""V23.1 Offline Paper Fill Engine.

This module simulates a fill from an already validated offline paper order.
It never imports a broker/network client and never changes an account balance
or position.  A caller-supplied offline price is the only price input.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid


VERSION = "V23.1"
CONFIRMATION_TEXT = "SIMULATE OFFLINE PAPER FILL V23.1"
OUTPUT_DIRECTORY = Path("backtest_outputs")
PRICE_QUANTUM = Decimal("0.0001")
MONEY_QUANTUM = Decimal("0.01")
QUANTITY_QUANTUM = Decimal("0.000001")


@dataclass(frozen=True)
class OfflinePaperFillEngineV231Policy:
    required_order_version: str = "V21.1"
    required_order_status: str = "DRAFTED_IN_MEMORY"
    required_order_mode: str = "OFFLINE_PAPER_DRAFT"
    required_audit_version: str = "V23.0"
    required_audit_status: str = "AUDITED_IN_MEMORY"
    required_confirmation_text: str = CONFIRMATION_TEXT
    allowed_sides: tuple[str, ...] = ("BUY", "SELL")
    allowed_order_types: tuple[str, ...] = ("MARKET", "LIMIT")
    slippage_bps: int = 2
    fee_bps: int = 5
    require_order_hash: bool = True
    require_audit_certificate_hash: bool = True
    require_sources_unchanged: bool = True
    partial_fills_disabled: bool = True
    account_mutation_disabled: bool = True
    funds_reservation_disabled: bool = True
    holdings_reservation_disabled: bool = True
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
class OfflinePaperFillV231:
    paper_fill_id: str
    created_at: str
    fill_mode: str
    fill_status: str
    fill_reason: str
    source_order_result_id: str
    source_paper_order_id: str
    source_order_hash: str
    source_audit_result_id: str
    source_audit_certificate_id: str
    source_audit_certificate_hash: str
    operator: str
    symbol: str
    side: str
    order_type: str
    requested_quantity: float
    filled_quantity: float
    offline_reference_price: float
    limit_price: float | None
    simulated_fill_price: float | None
    gross_notional: float
    simulated_fee: float
    net_cash_effect: float
    account_mutated: bool
    funds_reserved: bool
    holdings_reserved: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    fill_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("fill_hash")
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OfflinePaperFillEngineV231Result:
    version: str
    created_at: str
    fill_result_id: str
    result_status: str
    source_order_result_id: str | None
    source_paper_order_id: str | None
    source_order_hash: str | None
    source_audit_result_id: str | None
    source_audit_certificate_hash: str | None
    paper_fill_id: str | None
    fill_hash: str | None
    fill_status: str | None
    policy_checks_passed: bool
    input_checks_passed: bool
    order_source_checks_passed: bool
    audit_source_checks_passed: bool
    source_linkage_checks_passed: bool
    source_unchanged_checks_passed: bool
    fill_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    fill_simulated: bool
    account_mutated: bool
    funds_reserved: bool
    holdings_reserved: bool
    execution_blocked: bool
    transmit: bool
    credentials_used: bool
    market_data_api_called: bool
    account_api_called: bool
    network_accessed: bool
    broker_api_called: bool
    broker_order_created: bool
    order_submitted: bool
    live_execution_authorized: bool
    fill_policy: OfflinePaperFillEngineV231Policy
    fill: OfflinePaperFillV231 | None
    reasons: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["fill_policy"] = self.fill_policy.to_dict()
        payload["fill"] = self.fill.to_dict() if self.fill else None
        return payload


def canonical_json(value: Any) -> str:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def sha256_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def validate_policy(policy: OfflinePaperFillEngineV231Policy) -> list[str]:
    if not isinstance(policy, OfflinePaperFillEngineV231Policy):
        return ["V23.1 Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_order_version": "V21.1",
        "required_order_status": "DRAFTED_IN_MEMORY",
        "required_order_mode": "OFFLINE_PAPER_DRAFT",
        "required_audit_version": "V23.0",
        "required_audit_status": "AUDITED_IN_MEMORY",
        "required_confirmation_text": CONFIRMATION_TEXT,
        "allowed_sides": ("BUY", "SELL"),
        "allowed_order_types": ("MARKET", "LIMIT"),
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 정책 오류입니다.")
    if not isinstance(policy.slippage_bps, int) or not 0 <= policy.slippage_bps <= 100:
        errors.append("slippage_bps는 0~100 정수여야 합니다.")
    if not isinstance(policy.fee_bps, int) or not 0 <= policy.fee_bps <= 100:
        errors.append("fee_bps는 0~100 정수여야 합니다.")
    for name, value in policy.to_dict().items():
        if name.startswith("require_") or name.endswith(("_disabled", "_forbidden")):
            if isinstance(value, bool) and value is not True:
                errors.append(f"{name}는 True여야 합니다.")
    return errors


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("time must be text")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed.astimezone(timezone.utc)


def _decimal(value: Any, name: str, positive: bool = True) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} 형식 오류입니다.")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{name} 형식 오류입니다.") from None
    if not result.is_finite() or (positive and result <= 0):
        raise ValueError(f"{name}는 유한한 양수여야 합니다.")
    return result


def _source_safety_ok(source: Any) -> bool:
    false_fields = (
        "funds_reserved",
        "holdings_reserved",
        "transmit",
        "credentials_used",
        "market_data_api_called",
        "account_api_called",
        "network_accessed",
        "broker_api_called",
        "broker_order_created",
        "order_submitted",
        "live_execution_authorized",
    )
    return all(getattr(source, name, False) is False for name in false_fields)


def _order_errors(source: Any, policy: OfflinePaperFillEngineV231Policy) -> list[str]:
    errors: list[str] = []
    if getattr(source, "version", None) != policy.required_order_version:
        errors.append("V21.1 주문 Source Version 오류입니다.")
    if getattr(source, "result_status", None) != policy.required_order_status:
        errors.append("V21.1 주문은 DRAFTED_IN_MEMORY 상태여야 합니다.")
    if getattr(source, "all_checks_passed", None) is not True:
        errors.append("V21.1 주문 검증이 완료되지 않았습니다.")
    order = getattr(source, "order", None)
    if order is None:
        errors.append("V21.1 주문 초안이 없습니다.")
        return errors
    if getattr(order, "order_mode", None) != policy.required_order_mode:
        errors.append("V21.1 주문 모드 오류입니다.")
    if getattr(order, "order_status", None) != policy.required_order_status:
        errors.append("V21.1 주문 상태 오류입니다.")
    if getattr(order, "side", None) not in policy.allowed_sides:
        errors.append("V21.1 주문 방향 오류입니다.")
    if getattr(order, "order_type", None) not in policy.allowed_order_types:
        errors.append("V21.1 주문 유형 오류입니다.")
    payload = order.payload_without_hash() if hasattr(order, "payload_without_hash") else {}
    if not payload or sha256_payload(payload) != getattr(order, "order_hash", None):
        errors.append("V21.1 주문 Hash 검증에 실패했습니다.")
    if getattr(source, "order_hash", None) != getattr(order, "order_hash", None):
        errors.append("V21.1 주문 Result 연결 Hash 오류입니다.")
    if not _source_safety_ok(source):
        errors.append("V21.1 주문 Source 안전 플래그 오류입니다.")
    return errors


def _audit_errors(source: Any, policy: OfflinePaperFillEngineV231Policy) -> list[str]:
    errors: list[str] = []
    if getattr(source, "version", None) != policy.required_audit_version:
        errors.append("V23.0 감사 Source Version 오류입니다.")
    if getattr(source, "result_status", None) != policy.required_audit_status:
        errors.append("V23.0 감사가 완료 상태가 아닙니다.")
    if getattr(source, "all_checks_passed", None) is not True:
        errors.append("V23.0 감사 검증이 완료되지 않았습니다.")
    if getattr(source, "audit_completed", None) is not True:
        errors.append("V23.0 감사 완료 플래그 오류입니다.")
    certificate = getattr(source, "certificate", None)
    if certificate is None:
        errors.append("V23.0 감사 인증서가 없습니다.")
        return errors
    payload = (
        certificate.payload_without_hash()
        if hasattr(certificate, "payload_without_hash")
        else {}
    )
    if not payload or sha256_payload(payload) != getattr(certificate, "certificate_hash", None):
        errors.append("V23.0 감사 인증서 Hash 검증에 실패했습니다.")
    if getattr(source, "integrity_certificate_hash", None) != getattr(
        certificate, "certificate_hash", None
    ):
        errors.append("V23.0 감사 Result 연결 Hash 오류입니다.")
    if getattr(source, "ledger_modified", None) is not False:
        errors.append("V23.0 감사 Source 변경 플래그 오류입니다.")
    if not _source_safety_ok(source):
        errors.append("V23.0 감사 Source 안전 플래그 오류입니다.")
    return errors


def _result(
    policy: OfflinePaperFillEngineV231Policy,
    now: datetime,
    status: str,
    reasons: list[str],
    order_source: Any = None,
    audit_source: Any = None,
    fill: OfflinePaperFillV231 | None = None,
    *,
    policy_ok: bool = False,
    input_ok: bool = False,
    order_ok: bool = False,
    audit_ok: bool = False,
    linkage_ok: bool = False,
    unchanged_ok: bool = False,
    hash_ok: bool = False,
) -> OfflinePaperFillEngineV231Result:
    all_ok = all(
        (policy_ok, input_ok, order_ok, audit_ok, linkage_ok, unchanged_ok, hash_ok)
    )
    order = getattr(order_source, "order", None)
    certificate = getattr(audit_source, "certificate", None)
    return OfflinePaperFillEngineV231Result(
        version=VERSION,
        created_at=now.isoformat(),
        fill_result_id=str(uuid.uuid4()),
        result_status=status,
        source_order_result_id=getattr(order_source, "order_result_id", None),
        source_paper_order_id=getattr(order, "paper_order_id", None),
        source_order_hash=getattr(order, "order_hash", None),
        source_audit_result_id=getattr(audit_source, "audit_result_id", None),
        source_audit_certificate_hash=getattr(certificate, "certificate_hash", None),
        paper_fill_id=fill.paper_fill_id if fill else None,
        fill_hash=fill.fill_hash if fill else None,
        fill_status=fill.fill_status if fill else None,
        policy_checks_passed=policy_ok,
        input_checks_passed=input_ok,
        order_source_checks_passed=order_ok,
        audit_source_checks_passed=audit_ok,
        source_linkage_checks_passed=linkage_ok,
        source_unchanged_checks_passed=unchanged_ok,
        fill_hash_checks_passed=hash_ok,
        safety_checks_passed=all_ok,
        all_checks_passed=all_ok,
        fill_simulated=fill is not None,
        account_mutated=False,
        funds_reserved=False,
        holdings_reserved=False,
        execution_blocked=True,
        transmit=False,
        credentials_used=False,
        market_data_api_called=False,
        account_api_called=False,
        network_accessed=False,
        broker_api_called=False,
        broker_order_created=False,
        order_submitted=False,
        live_execution_authorized=False,
        fill_policy=policy,
        fill=fill,
        reasons=reasons,
    )


def simulate_offline_paper_fill_v23_1(
    order_source: Any,
    audit_source: Any,
    operator: Any,
    confirmation_text: Any,
    offline_reference_price: Any,
    policy: OfflinePaperFillEngineV231Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperFillEngineV231Result:
    policy = policy or OfflinePaperFillEngineV231Policy()
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    policy_errors = validate_policy(policy)
    if policy_errors:
        return _result(policy, now, "BLOCKED", policy_errors)
    input_errors: list[str] = []
    if not isinstance(operator, str) or not operator.strip():
        input_errors.append("Operator는 비어 있지 않은 문자열이어야 합니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("V23.1 확인 문구가 일치하지 않습니다.")
    try:
        reference = _decimal(offline_reference_price, "offline_reference_price")
    except ValueError as exc:
        input_errors.append(str(exc))
        reference = Decimal("0")
    if input_errors:
        return _result(policy, now, "BLOCKED", input_errors, policy_ok=True)

    order_errors = _order_errors(order_source, policy)
    if order_errors:
        return _result(
            policy, now, "BLOCKED", order_errors, order_source, audit_source,
            policy_ok=True, input_ok=True,
        )
    audit_errors = _audit_errors(audit_source, policy)
    if audit_errors:
        return _result(
            policy, now, "BLOCKED", audit_errors, order_source, audit_source,
            policy_ok=True, input_ok=True, order_ok=True,
        )

    order_before = canonical_json(order_source)
    audit_before = canonical_json(audit_source)
    order = order_source.order
    certificate = audit_source.certificate
    if getattr(order, "operator", None) != operator.strip():
        return _result(
            policy, now, "BLOCKED", ["Operator가 V21.1 주문과 일치하지 않습니다."],
            order_source, audit_source, policy_ok=True, input_ok=True,
            order_ok=True, audit_ok=True,
        )
    try:
        if now < _parse_utc(order.created_at) or now < _parse_utc(certificate.audited_at):
            raise ValueError("V23.1 시간이 Source 시간보다 이전입니다.")
    except ValueError as exc:
        return _result(
            policy, now, "BLOCKED", [str(exc)], order_source, audit_source,
            policy_ok=True, input_ok=True, order_ok=True, audit_ok=True,
        )

    quantity = _decimal(order.quantity, "quantity").quantize(QUANTITY_QUANTUM)
    limit = (
        _decimal(order.limit_price, "limit_price")
        if order.order_type == "LIMIT"
        else None
    )
    should_fill = (
        order.order_type == "MARKET"
        or (order.side == "BUY" and reference <= limit)
        or (order.side == "SELL" and reference >= limit)
    )
    bps = Decimal(policy.slippage_bps) / Decimal(10_000)
    slipped = reference * (Decimal("1") + bps if order.side == "BUY" else Decimal("1") - bps)
    if should_fill and limit is not None:
        slipped = min(slipped, limit) if order.side == "BUY" else max(slipped, limit)
    fill_price = slipped.quantize(PRICE_QUANTUM, rounding=ROUND_HALF_UP) if should_fill else None
    filled_quantity = quantity if should_fill else Decimal("0")
    gross = (
        (filled_quantity * fill_price).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        if fill_price is not None
        else Decimal("0")
    )
    fee = (
        (gross * Decimal(policy.fee_bps) / Decimal(10_000)).quantize(
            MONEY_QUANTUM, rounding=ROUND_HALF_UP
        )
        if should_fill
        else Decimal("0")
    )
    net = Decimal("0")
    if should_fill:
        net = -(gross + fee) if order.side == "BUY" else gross - fee
    payload = {
        "paper_fill_id": str(uuid.uuid4()),
        "created_at": now.isoformat(),
        "fill_mode": "OFFLINE_PAPER_SIMULATION",
        "fill_status": "FILLED" if should_fill else "NOT_FILLED",
        "fill_reason": "OFFLINE_PRICE_MATCHED" if should_fill else "LIMIT_NOT_MARKETABLE",
        "source_order_result_id": order_source.order_result_id,
        "source_paper_order_id": order.paper_order_id,
        "source_order_hash": order.order_hash,
        "source_audit_result_id": audit_source.audit_result_id,
        "source_audit_certificate_id": certificate.integrity_certificate_id,
        "source_audit_certificate_hash": certificate.certificate_hash,
        "operator": operator.strip(),
        "symbol": order.symbol,
        "side": order.side,
        "order_type": order.order_type,
        "requested_quantity": float(quantity),
        "filled_quantity": float(filled_quantity),
        "offline_reference_price": float(reference.quantize(PRICE_QUANTUM)),
        "limit_price": float(limit.quantize(PRICE_QUANTUM)) if limit else None,
        "simulated_fill_price": float(fill_price) if fill_price else None,
        "gross_notional": float(gross),
        "simulated_fee": float(fee),
        "net_cash_effect": float(net),
        "account_mutated": False,
        "funds_reserved": False,
        "holdings_reserved": False,
        "transmit": False,
        "credentials_used": False,
        "market_data_api_called": False,
        "account_api_called": False,
        "network_accessed": False,
        "broker_api_called": False,
        "broker_order_created": False,
        "order_submitted": False,
        "live_execution_authorized": False,
    }
    fill = OfflinePaperFillV231(**payload, fill_hash=sha256_payload(payload))
    unchanged = order_before == canonical_json(order_source) and audit_before == canonical_json(audit_source)
    hash_ok = sha256_payload(fill.payload_without_hash()) == fill.fill_hash
    if not unchanged or not hash_ok:
        return _result(
            policy, now, "FAILED", ["V23.1 생성 무결성 검사에 실패했습니다."],
            order_source, audit_source, policy_ok=True, input_ok=True,
            order_ok=True, audit_ok=True, linkage_ok=True,
            unchanged_ok=unchanged, hash_ok=hash_ok,
        )
    return _result(
        policy, now, "SIMULATED_IN_MEMORY", [], order_source, audit_source, fill,
        policy_ok=True, input_ok=True, order_ok=True, audit_ok=True,
        linkage_ok=True, unchanged_ok=True, hash_ok=True,
    )


def verify_offline_paper_fill(fill: OfflinePaperFillV231) -> tuple[bool, list[str]]:
    if not isinstance(fill, OfflinePaperFillV231):
        return False, ["V23.1 Fill 형식 오류입니다."]
    errors: list[str] = []
    if sha256_payload(fill.payload_without_hash()) != fill.fill_hash:
        errors.append("V23.1 Fill Hash가 일치하지 않습니다.")
    if fill.fill_mode != "OFFLINE_PAPER_SIMULATION":
        errors.append("V23.1 Fill Mode 오류입니다.")
    if fill.fill_status not in {"FILLED", "NOT_FILLED"}:
        errors.append("V23.1 Fill Status 오류입니다.")
    if any(
        (
            fill.account_mutated,
            fill.funds_reserved,
            fill.holdings_reserved,
            fill.transmit,
            fill.credentials_used,
            fill.market_data_api_called,
            fill.account_api_called,
            fill.network_accessed,
            fill.broker_api_called,
            fill.broker_order_created,
            fill.order_submitted,
            fill.live_execution_authorized,
        )
    ):
        errors.append("V23.1 안전 플래그 오류입니다.")
    return not errors, errors


def save_fill_result(
    result: OfflinePaperFillEngineV231Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    path = output_directory / f"offline_paper_fill_v23_1_{result.fill_result_id}.json"
    path.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result.report_path = str(path)
    latest = output_directory / "offline_paper_fill_v23_1_latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    result.latest_path = str(latest)
    return path


def load_fill_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
