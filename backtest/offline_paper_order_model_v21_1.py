import hashlib
import json
import math
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backtest.offline_paper_trading_account_v21_0 import (
    OfflinePaperTradingAccountV210,
    OfflinePaperTradingAccountV210Result,
    canonical_json,
    verify_offline_paper_account,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "offline_paper_order_model_v21_1"
)
REQUIRED_ORDER_TEXT = "CREATE OFFLINE PAPER ORDER DRAFT V21.1"
SYMBOL_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")


@dataclass(frozen=True)
class OfflinePaperOrderV211Policy:
    required_source_version: str = "V21.0"
    required_source_status: str = "CREATED_IN_MEMORY"
    required_account_mode: str = "OFFLINE_PAPER"
    required_account_status: str = "READY_IN_MEMORY"
    required_confirmation_text: str = REQUIRED_ORDER_TEXT
    required_currency: str = "USD"
    allowed_sides: tuple[str, ...] = ("BUY", "SELL")
    allowed_order_types: tuple[str, ...] = ("MARKET", "LIMIT")
    allowed_time_in_force: tuple[str, ...] = ("DAY",)
    minimum_quantity: float = 0.000001
    maximum_quantity: float = 1_000_000.0
    maximum_estimated_notional: float = 1_000_000.0
    require_same_operator: bool = True
    require_source_unchanged: bool = True
    require_offline_reference_price: bool = True
    short_selling_disabled: bool = True
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
class OfflinePaperOrderV211:
    paper_order_id: str
    created_at: str
    order_mode: str
    order_status: str
    account_id: str
    account_hash: str
    operator: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    currency: str
    time_in_force: str
    reference_price: float | None
    limit_price: float | None
    estimated_price: float
    estimated_notional: float
    cash_balance_snapshot: float
    position_quantity_snapshot: float
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
    order_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("order_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OfflinePaperOrderV211Result:
    version: str
    created_at: str
    order_result_id: str
    result_status: str
    result_status_label: str
    source_v21_0_result_id: str | None
    source_account_id: str | None
    source_account_hash: str | None
    paper_order_id: str | None
    order_hash: str | None
    symbol: str | None
    side: str | None
    order_type: str | None
    quantity: float
    estimated_notional: float
    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    source_linkage_checks_passed: bool
    source_unchanged_checks_passed: bool
    order_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool
    order_draft_created: bool
    paper_order_created: bool
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
    order_policy: OfflinePaperOrderV211Policy
    order: OfflinePaperOrderV211 | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["order_policy"] = self.order_policy.to_dict()
        payload["order"] = self.order.to_dict() if self.order else None
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


def _valid_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def validate_policy(policy: OfflinePaperOrderV211Policy) -> list[str]:
    if not isinstance(policy, OfflinePaperOrderV211Policy):
        return ["Offline Paper Order Policy 형식 오류입니다."]
    errors: list[str] = []
    expected = {
        "required_source_version": "V21.0",
        "required_source_status": "CREATED_IN_MEMORY",
        "required_account_mode": "OFFLINE_PAPER",
        "required_account_status": "READY_IN_MEMORY",
        "required_confirmation_text": REQUIRED_ORDER_TEXT,
        "required_currency": "USD",
        "allowed_sides": ("BUY", "SELL"),
        "allowed_order_types": ("MARKET", "LIMIT"),
        "allowed_time_in_force": ("DAY",),
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(f"{name} 값이 V21.1 기준과 다릅니다.")
    if (
        not _valid_number(policy.minimum_quantity)
        or not _valid_number(policy.maximum_quantity)
        or not _valid_number(policy.maximum_estimated_notional)
        or policy.minimum_quantity <= 0
        or policy.maximum_quantity < policy.minimum_quantity
        or policy.maximum_estimated_notional <= 0
    ):
        errors.append("수량 또는 예상 주문금액 한도가 올바르지 않습니다.")
    for name in (
        "require_same_operator",
        "require_source_unchanged",
        "require_offline_reference_price",
        "short_selling_disabled",
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
            errors.append(f"{name}는 V21.1에서 True여야 합니다.")
    return errors


def _safe_source(source: OfflinePaperTradingAccountV210Result) -> bool:
    return not any(
        (
            source.paper_order_execution_authorized,
            source.automatic_execution_authorized,
            not source.execution_blocked,
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


def _position_quantity(
    account: OfflinePaperTradingAccountV210,
    symbol: str,
) -> float:
    return sum(
        position.quantity
        for position in account.positions
        if position.symbol == symbol
    )


def verify_offline_paper_order(
    order: OfflinePaperOrderV211,
) -> tuple[bool, list[str]]:
    if not isinstance(order, OfflinePaperOrderV211):
        return False, ["Offline Paper Order 형식 오류입니다."]
    errors: list[str] = []
    if order.order_mode != "OFFLINE_PAPER_DRAFT":
        errors.append("Order Mode가 OFFLINE_PAPER_DRAFT가 아닙니다.")
    if order.order_status != "DRAFTED_IN_MEMORY":
        errors.append("Order Status가 DRAFTED_IN_MEMORY가 아닙니다.")
    if not SYMBOL_PATTERN.fullmatch(order.symbol):
        errors.append("Symbol 형식이 올바르지 않습니다.")
    if order.side not in ("BUY", "SELL"):
        errors.append("Side가 BUY 또는 SELL이 아닙니다.")
    if order.order_type not in ("MARKET", "LIMIT"):
        errors.append("Order Type이 MARKET 또는 LIMIT이 아닙니다.")
    if order.currency != "USD" or order.time_in_force != "DAY":
        errors.append("Currency 또는 Time In Force가 올바르지 않습니다.")
    if not all(
        (
            order.estimated_price > 0,
            order.quantity > 0,
            order.estimated_notional
            == round(order.estimated_price * order.quantity, 2),
            not order.funds_reserved,
            not order.holdings_reserved,
            not order.order_execution_authorized,
            not order.automatic_execution_authorized,
            not order.transmit,
            not order.credentials_used,
            not order.market_data_api_called,
            not order.account_api_called,
            not order.network_accessed,
            not order.broker_api_called,
            not order.broker_order_created,
            not order.order_submitted,
            not order.live_order_created,
            not order.live_execution_authorized,
        )
    ):
        errors.append("Offline Paper Order 계산 또는 안전장치 오류입니다.")
    if order.order_type == "MARKET":
        if order.reference_price is None or order.limit_price is not None:
            errors.append("MARKET Order의 가격 필드가 올바르지 않습니다.")
    if order.order_type == "LIMIT":
        if order.limit_price is None:
            errors.append("LIMIT Order에 Limit Price가 없습니다.")
    if order.order_hash != sha256_payload(order.payload_without_hash()):
        errors.append("Offline Paper Order Hash가 일치하지 않습니다.")
    return not errors, errors


def _result(
    policy_value: OfflinePaperOrderV211Policy,
    now: datetime,
    status: str,
    reasons: list[str],
    source_result: OfflinePaperTradingAccountV210Result | None = None,
    order_value: OfflinePaperOrderV211 | None = None,
    **checks: bool,
) -> OfflinePaperOrderV211Result:
    created = status == "DRAFTED_IN_MEMORY" and order_value is not None
    account = source_result.account if source_result else None
    return OfflinePaperOrderV211Result(
        version="V21.1",
        created_at=now.isoformat(),
        order_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=(
            "Offline Paper Order 초안 생성 완료"
            if created
            else "Offline Paper Order 차단"
            if status == "BLOCKED"
            else "Offline Paper Order 실패"
        ),
        source_v21_0_result_id=(
            source_result.account_result_id if source_result else None
        ),
        source_account_id=account.account_id if account else None,
        source_account_hash=account.account_hash if account else None,
        paper_order_id=order_value.paper_order_id if order_value else None,
        order_hash=order_value.order_hash if order_value else None,
        symbol=order_value.symbol if order_value else None,
        side=order_value.side if order_value else None,
        order_type=order_value.order_type if order_value else None,
        quantity=order_value.quantity if order_value else 0.0,
        estimated_notional=(
            order_value.estimated_notional if order_value else 0.0
        ),
        policy_checks_passed=checks.get("policy", False),
        input_checks_passed=checks.get("input", False),
        source_checks_passed=checks.get("source", False),
        source_linkage_checks_passed=checks.get("linkage", False),
        source_unchanged_checks_passed=checks.get("unchanged", False),
        order_hash_checks_passed=checks.get("hash", False),
        safety_checks_passed=True,
        all_checks_passed=created,
        order_draft_created=created,
        paper_order_created=created,
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
        order_policy=policy_value,
        order=order_value,
        reasons=reasons,
        warnings=[
            "V21.1은 주문 초안만 생성하며 잔액과 보유수량을 변경하지 않습니다.",
            "가격은 외부 시세가 아닌 사용자가 입력한 오프라인 참고값입니다.",
            "Broker API, Network, 실제 주문 및 Live Execution은 차단됩니다.",
        ],
        next_actions=[
            "V21.2 Offline Paper Order Validation 단계에서 주문 초안을 재검증합니다."
        ],
    )


def create_offline_paper_order_v21_1(
    source: Any,
    operator: Any,
    confirmation_text: Any,
    symbol: Any,
    side: Any,
    order_type: Any,
    quantity: Any,
    reference_price: Any = None,
    limit_price: Any = None,
    currency: Any = "USD",
    time_in_force: Any = "DAY",
    policy: OfflinePaperOrderV211Policy | None = None,
    now: datetime | None = None,
) -> OfflinePaperOrderV211Result:
    policy = policy or OfflinePaperOrderV211Policy()
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        now = datetime.now(timezone.utc)
    policy_errors = validate_policy(policy)
    if policy_errors:
        safe_policy = (
            policy
            if isinstance(policy, OfflinePaperOrderV211Policy)
            else OfflinePaperOrderV211Policy()
        )
        return _result(safe_policy, now, "BLOCKED", policy_errors)
    if not isinstance(source, OfflinePaperTradingAccountV210Result):
        return _result(
            policy,
            now,
            "FAILED",
            ["Source는 V21.0 Offline Paper Trading Account Result여야 합니다."],
            policy=True,
        )
    source_before = canonical_json(source.to_dict())
    source_errors: list[str] = []
    account = source.account
    if source.version != policy.required_source_version:
        source_errors.append("V21.0 Source Version이 아닙니다.")
    if source.result_status != policy.required_source_status:
        source_errors.append("V21.0 Account 생성 완료 상태가 아닙니다.")
    if account is None:
        source_errors.append("V21.0 Account가 없습니다.")
    else:
        valid_account, account_errors = verify_offline_paper_account(account)
        if not valid_account or account_errors:
            source_errors.append("V21.0 Account Hash 검증 실패입니다.")
        if source.account_id != account.account_id:
            source_errors.append("V21.0 Result와 Account ID 연결 오류입니다.")
        if source.account_hash != account.account_hash:
            source_errors.append("V21.0 Result와 Account Hash 연결 오류입니다.")
        if account.account_mode != policy.required_account_mode:
            source_errors.append("V21.0 Account Mode가 올바르지 않습니다.")
        if account.account_status != policy.required_account_status:
            source_errors.append("V21.0 Account Status가 올바르지 않습니다.")
    if not source.all_checks_passed or not source.account_created:
        source_errors.append("V21.0 Source 검사가 완료되지 않았습니다.")
    if not _safe_source(source):
        source_errors.append("V21.0 Source 안전장치 검증 실패입니다.")
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
    elif policy.require_same_operator and operator.strip() != account.operator:
        input_errors.append("Operator가 V21.0 Account와 일치하지 않습니다.")
    if confirmation_text != policy.required_confirmation_text:
        input_errors.append("V21.1 확인 문구가 일치하지 않습니다.")
    if not isinstance(symbol, str) or not SYMBOL_PATTERN.fullmatch(symbol):
        input_errors.append("Symbol은 대문자 종목코드 형식이어야 합니다.")
    if side not in policy.allowed_sides:
        input_errors.append("Side는 BUY 또는 SELL이어야 합니다.")
    if order_type not in policy.allowed_order_types:
        input_errors.append("Order Type은 MARKET 또는 LIMIT이어야 합니다.")
    if currency != policy.required_currency:
        input_errors.append("V21.1 Currency는 USD만 허용됩니다.")
    if time_in_force not in policy.allowed_time_in_force:
        input_errors.append("V21.1 Time In Force는 DAY만 허용됩니다.")
    if not _valid_number(quantity):
        input_errors.append("Quantity는 유한한 숫자여야 합니다.")
        normalized_quantity = 0.0
    else:
        normalized_quantity = round(float(quantity), 6)
        if not (
            policy.minimum_quantity
            <= normalized_quantity
            <= policy.maximum_quantity
        ):
            input_errors.append("Quantity가 V21.1 허용 범위를 벗어났습니다.")

    normalized_reference: float | None = None
    normalized_limit: float | None = None
    estimated_price = 0.0
    if order_type == "MARKET":
        if not _valid_number(reference_price) or float(reference_price) <= 0:
            input_errors.append("MARKET Order에는 양수 Offline Reference Price가 필요합니다.")
        else:
            normalized_reference = round(float(reference_price), 6)
            estimated_price = normalized_reference
        if limit_price is not None:
            input_errors.append("MARKET Order에는 Limit Price를 입력할 수 없습니다.")
    elif order_type == "LIMIT":
        if not _valid_number(limit_price) or float(limit_price) <= 0:
            input_errors.append("LIMIT Order에는 양수 Limit Price가 필요합니다.")
        else:
            normalized_limit = round(float(limit_price), 6)
            estimated_price = normalized_limit
        if reference_price is not None:
            if not _valid_number(reference_price) or float(reference_price) <= 0:
                input_errors.append("Offline Reference Price가 올바르지 않습니다.")
            else:
                normalized_reference = round(float(reference_price), 6)

    estimated_notional = round(
        normalized_quantity * estimated_price,
        2,
    )
    if estimated_notional > policy.maximum_estimated_notional:
        input_errors.append("예상 주문금액이 V21.1 한도를 초과했습니다.")
    position_quantity = (
        _position_quantity(account, symbol)
        if isinstance(symbol, str)
        else 0.0
    )
    if side == "BUY" and estimated_notional > account.cash_balance:
        input_errors.append("예상 주문금액이 가상 현금잔액을 초과했습니다.")
    if (
        side == "SELL"
        and policy.short_selling_disabled
        and normalized_quantity > position_quantity
    ):
        input_errors.append("보유수량을 초과한 매도 또는 공매도는 차단됩니다.")
    try:
        account_created_at = datetime.fromisoformat(account.created_at)
        if now < account_created_at:
            input_errors.append("Order 시간이 V21.0 Account보다 이전입니다.")
    except (TypeError, ValueError):
        input_errors.append("V21.0 Account 시간이 올바르지 않습니다.")
    if input_errors:
        return _result(
            policy,
            now,
            "BLOCKED",
            input_errors,
            source_result=source,
            policy=True,
            source=True,
            linkage=True,
        )

    payload = {
        "paper_order_id": str(uuid.uuid4()),
        "created_at": now.isoformat(),
        "order_mode": "OFFLINE_PAPER_DRAFT",
        "order_status": "DRAFTED_IN_MEMORY",
        "account_id": account.account_id,
        "account_hash": account.account_hash,
        "operator": operator.strip(),
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": normalized_quantity,
        "currency": "USD",
        "time_in_force": "DAY",
        "reference_price": normalized_reference,
        "limit_price": normalized_limit,
        "estimated_price": estimated_price,
        "estimated_notional": estimated_notional,
        "cash_balance_snapshot": account.cash_balance,
        "position_quantity_snapshot": position_quantity,
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
    order = OfflinePaperOrderV211(
        **payload,
        order_hash=sha256_payload(payload),
    )
    valid_order, order_errors = verify_offline_paper_order(order)
    unchanged = source_before == canonical_json(source.to_dict())
    if not unchanged:
        return _result(
            policy,
            now,
            "FAILED",
            ["V21.1 생성 중 V21.0 Source가 변경되었습니다."],
            source_result=source,
            policy=True,
            input=True,
            source=True,
            linkage=True,
        )
    if not valid_order:
        return _result(
            policy,
            now,
            "FAILED",
            order_errors,
            source_result=source,
            policy=True,
            input=True,
            source=True,
            linkage=True,
            unchanged=True,
        )
    return _result(
        policy,
        now,
        "DRAFTED_IN_MEMORY",
        [],
        source_result=source,
        order_value=order,
        policy=True,
        input=True,
        source=True,
        linkage=True,
        unchanged=True,
        hash=True,
    )


def save_order_result(
    result: OfflinePaperOrderV211Result,
    output_directory: Path = OUTPUT_DIRECTORY,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    stamp = result.created_at.replace(":", "-").replace("+", "_")
    report_path = output_directory / f"offline_paper_order_{stamp}.json"
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


def load_order_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
