import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.certified_paper_run_launch_authorization import (
    CertifiedPaperRunLaunchAuthorization,
    CertifiedPaperRunLaunchAuthorizationResult,
    verify_launch_authorization,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTHORIZED_PAPER_RUN_EXECUTION_ENVELOPE_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "authorized_paper_run_execution_envelope"
)

REQUIRED_ENVELOPE_TEXT = (
    "BUILD AUTHORIZED PAPER RUN ENVELOPE"
)
VALID_ENVELOPE_STATUSES = {
    "SEALED",
    "BLOCKED",
    "FAILED",
}
VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


@dataclass(frozen=True)
class AuthorizedPaperRunExecutionEnvelopePolicy:
    """V12.9 Paper 실행 봉투 정책입니다."""

    required_authorization_version: str = "V12.8"
    required_authorization_status: str = "AUTHORIZED"
    required_confirmation_text: str = (
        REQUIRED_ENVELOPE_TEXT
    )
    maximum_order_count: int = 20
    maximum_quantity_per_order: int = 10000
    maximum_notional_per_order: float = 100000.0
    hash_algorithm: str = "SHA256"

    require_unexpired_authorization: bool = True
    require_authorization_hash: bool = True
    require_same_operator: bool = True
    require_unique_order_ids: bool = True
    require_authorized_symbols: bool = True
    require_source_safety: bool = True

    envelope_only: bool = True
    automatic_execution_disabled: bool = True
    broker_execution_disabled: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PaperEnvelopeOrder:
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: int
    limit_price: float | None
    estimated_notional: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AuthorizedPaperRunExecutionEnvelope:
    envelope_id: str
    created_at: str
    expires_at: str
    envelope_status: str

    authorization_result_id: str
    authorization_id: str
    authorization_hash: str
    certificate_id: str
    preflight_id: str
    trading_date: str
    operator: str

    total_order_count: int
    total_estimated_notional: float
    orders: tuple[PaperEnvelopeOrder, ...]

    paper_envelope_authorized: bool
    paper_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool
    envelope_hash: str

    def payload_without_hash(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["orders"] = [
            order.to_dict()
            for order in self.orders
        ]
        payload.pop("envelope_hash", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["orders"] = [
            order.to_dict()
            for order in self.orders
        ]
        return payload


@dataclass
class AuthorizedPaperRunExecutionEnvelopeResult:
    version: str
    created_at: str
    envelope_result_id: str
    result_status: str
    result_status_label: str

    envelope_id: str | None
    envelope_hash: str | None
    expires_at: str | None
    order_count: int
    total_estimated_notional: float

    policy_checks_passed: bool
    input_checks_passed: bool
    source_checks_passed: bool
    authorization_checks_passed: bool
    operator_checks_passed: bool
    order_checks_passed: bool
    envelope_hash_checks_passed: bool
    safety_checks_passed: bool
    all_checks_passed: bool

    paper_envelope_authorized: bool
    paper_execution_authorized: bool
    automatic_execution_authorized: bool
    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    envelope_policy: (
        AuthorizedPaperRunExecutionEnvelopePolicy
    )
    envelope: (
        AuthorizedPaperRunExecutionEnvelope | None
    )
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["envelope_policy"] = (
            self.envelope_policy.to_dict()
        )
        payload["envelope"] = (
            self.envelope.to_dict()
            if self.envelope is not None
            else None
        )
        return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def calculate_envelope_hash(
    payload: dict[str, Any],
) -> str:
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


def write_json_file(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )
    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )
    temporary_path.replace(path)


def read_json_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(
            "JSON 최상위 값은 object여야 합니다."
        )
    return payload


def validate_envelope_policy(
    policy: AuthorizedPaperRunExecutionEnvelopePolicy,
) -> tuple[bool, list[str]]:
    if not isinstance(
        policy,
        AuthorizedPaperRunExecutionEnvelopePolicy,
    ):
        return (
            False,
            ["Execution Envelope Policy 형식이 올바르지 않습니다."],
        )
    errors: list[str] = []
    expected = {
        "required_authorization_version": "V12.8",
        "required_authorization_status": "AUTHORIZED",
        "required_confirmation_text": (
            REQUIRED_ENVELOPE_TEXT
        ),
        "hash_algorithm": "SHA256",
    }
    for name, value in expected.items():
        if getattr(policy, name) != value:
            errors.append(
                f"{name} 값이 V12.9 기준과 다릅니다."
            )
    if (
        policy.maximum_order_count <= 0
        or policy.maximum_quantity_per_order <= 0
        or policy.maximum_notional_per_order <= 0
    ):
        errors.append(
            "Envelope 숫자 기준이 올바르지 않습니다."
        )
    for name in (
        "require_unexpired_authorization",
        "require_authorization_hash",
        "require_same_operator",
        "require_unique_order_ids",
        "require_authorized_symbols",
        "require_source_safety",
        "envelope_only",
        "automatic_execution_disabled",
        "broker_execution_disabled",
        "live_execution_disabled",
    ):
        if getattr(policy, name) is not True:
            errors.append(
                f"{name}는 V12.9에서 True여야 합니다."
            )
    return (not errors, errors)


def validate_authorization_source(
    result: Any,
) -> tuple[
    bool,
    bool,
    bool,
    CertifiedPaperRunLaunchAuthorization | None,
    list[str],
]:
    if not isinstance(
        result,
        CertifiedPaperRunLaunchAuthorizationResult,
    ):
        return (
            False,
            False,
            False,
            None,
            ["Authorization Result는 V12.8 형식이어야 합니다."],
        )
    errors: list[str] = []
    source_valid = bool(
        result.version == "V12.8"
        and result.result_status == "AUTHORIZED"
        and result.all_checks_passed
        and result.paper_launch_authorized
        and result.authorizations
    )
    authorization = (
        result.authorizations[-1]
        if source_valid
        else None
    )
    if authorization is not None:
        (
            authorization_valid,
            _,
            authorization_errors,
        ) = verify_launch_authorization(authorization)
        errors.extend(authorization_errors)
    else:
        authorization_valid = False
    if not source_valid:
        errors.append(
            "정상적으로 AUTHORIZED된 V12.8 Source가 아닙니다."
        )
    safety_valid = bool(
        result.paper_execution_authorized is False
        and result.automatic_execution_authorized is False
        and result.execution_blocked is True
        and result.broker_api_called is False
        and result.broker_order_created is False
        and result.live_order_created is False
        and result.live_execution_authorized is False
    )
    if not safety_valid:
        errors.append(
            "Authorization Source에 실행 안전 오류가 있습니다."
        )
    return (
        source_valid,
        authorization_valid,
        safety_valid,
        authorization,
        errors,
    )


def normalize_orders(
    orders: Any,
    authorization: CertifiedPaperRunLaunchAuthorization,
    policy: AuthorizedPaperRunExecutionEnvelopePolicy,
) -> tuple[
    tuple[PaperEnvelopeOrder, ...],
    bool,
    list[str],
]:
    if not isinstance(orders, (tuple, list)):
        return (
            (),
            False,
            ["Orders는 tuple 또는 list여야 합니다."],
        )
    errors: list[str] = []
    normalized: list[PaperEnvelopeOrder] = []
    if not orders:
        errors.append(
            "최소 한 개의 Paper Order가 필요합니다."
        )
    if len(orders) > policy.maximum_order_count:
        errors.append(
            "Order 수가 Policy 제한을 초과했습니다."
        )
    authorized_symbols = {
        symbol.upper()
        for symbol in authorization.symbols
    }
    seen_ids: set[str] = set()
    for index, raw in enumerate(orders, start=1):
        if not isinstance(raw, dict):
            errors.append(
                f"{index}번 Order 형식이 object가 아닙니다."
            )
            continue
        order_id = raw.get("order_id")
        symbol = raw.get("symbol")
        side = raw.get("side")
        order_type = raw.get("order_type")
        quantity = raw.get("quantity")
        limit_price = raw.get("limit_price")
        basic_valid = bool(
            isinstance(order_id, str)
            and order_id.strip()
            and isinstance(symbol, str)
            and symbol.strip()
            and isinstance(side, str)
            and side.upper() in VALID_SIDES
            and isinstance(order_type, str)
            and order_type.upper() in VALID_ORDER_TYPES
            and isinstance(quantity, int)
            and not isinstance(quantity, bool)
            and 0 < quantity
            <= policy.maximum_quantity_per_order
        )
        if not basic_valid:
            errors.append(
                f"{index}번 Order 기본 값이 올바르지 않습니다."
            )
            continue
        order_id = order_id.strip()
        symbol = symbol.strip().upper()
        side = side.upper()
        order_type = order_type.upper()
        if order_id in seen_ids:
            errors.append(
                f"{order_id} Order ID가 중복되었습니다."
            )
        seen_ids.add(order_id)
        if symbol not in authorized_symbols:
            errors.append(
                f"{symbol}은 Authorization 종목이 아닙니다."
            )
        if order_type == "LIMIT":
            if (
                not isinstance(limit_price, (int, float))
                or isinstance(limit_price, bool)
                or limit_price <= 0
            ):
                errors.append(
                    f"{order_id} LIMIT Price가 올바르지 않습니다."
                )
                continue
            price = float(limit_price)
        else:
            if limit_price is not None:
                errors.append(
                    f"{order_id} MARKET Order에는 Limit Price를 넣을 수 없습니다."
                )
                continue
            price = 0.0
        estimated_price = (
            price
            if order_type == "LIMIT"
            else float(raw.get("reference_price", 0.0))
        )
        if estimated_price <= 0:
            errors.append(
                f"{order_id} 예상 가격이 올바르지 않습니다."
            )
            continue
        notional = quantity * estimated_price
        if notional > policy.maximum_notional_per_order:
            errors.append(
                f"{order_id} Notional이 Policy 제한을 초과했습니다."
            )
        normalized.append(
            PaperEnvelopeOrder(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                limit_price=(
                    price
                    if order_type == "LIMIT"
                    else None
                ),
                estimated_notional=notional,
            )
        )
    return (
        tuple(normalized),
        bool(not errors and len(normalized) == len(orders)),
        errors,
    )


def verify_execution_envelope(
    envelope: AuthorizedPaperRunExecutionEnvelope,
    checked_at: datetime | None = None,
) -> tuple[bool, bool, list[str]]:
    errors: list[str] = []
    hash_valid = (
        envelope.envelope_hash
        == calculate_envelope_hash(
            envelope.payload_without_hash()
        )
    )
    if not hash_valid:
        errors.append(
            "Envelope Hash가 일치하지 않습니다."
        )
    try:
        time_valid = (
            checked_at or datetime.now()
        ) <= datetime.fromisoformat(envelope.expires_at)
    except (TypeError, ValueError):
        time_valid = False
    if not time_valid:
        errors.append(
            "Envelope가 만료되었습니다."
        )
    safety_valid = bool(
        envelope.paper_envelope_authorized is True
        and envelope.paper_execution_authorized is False
        and envelope.execution_blocked is True
        and envelope.broker_api_called is False
        and envelope.broker_order_created is False
        and envelope.live_order_created is False
        and envelope.live_execution_authorized is False
    )
    if not safety_valid:
        errors.append(
            "Envelope에 실행 안전 오류가 있습니다."
        )
    return (
        bool(hash_valid and time_valid and safety_valid),
        time_valid,
        errors,
    )


def build_authorized_paper_run_execution_envelope(
    authorization_result: Any,
    orders: Any,
    envelope_operator: Any,
    confirmation_text: Any,
    envelope_policy: (
        AuthorizedPaperRunExecutionEnvelopePolicy
        | None
    ) = None,
) -> AuthorizedPaperRunExecutionEnvelopeResult:
    policy = (
        envelope_policy
        if envelope_policy is not None
        else AuthorizedPaperRunExecutionEnvelopePolicy()
    )
    policy_valid, policy_errors = (
        validate_envelope_policy(policy)
    )
    (
        source_valid,
        authorization_valid,
        source_safety_valid,
        authorization,
        source_errors,
    ) = validate_authorization_source(
        authorization_result
    )
    input_valid = bool(
        isinstance(envelope_operator, str)
        and envelope_operator.strip()
        and isinstance(confirmation_text, str)
    )
    operator_valid = bool(
        input_valid
        and authorization is not None
        and envelope_operator.strip()
        == authorization.operator
        and confirmation_text.strip()
        == policy.required_confirmation_text
    )
    operator_errors: list[str] = []
    if not input_valid:
        operator_errors.append(
            "Envelope Operator 또는 Confirmation 입력이 올바르지 않습니다."
        )
    elif authorization is not None:
        if envelope_operator.strip() != authorization.operator:
            operator_errors.append(
                "Envelope Operator가 Authorization Operator와 일치하지 않습니다."
            )
        if (
            confirmation_text.strip()
            != policy.required_confirmation_text
        ):
            operator_errors.append(
                "Envelope Confirmation Text가 일치하지 않습니다."
            )
    if authorization is not None:
        normalized_orders, orders_valid, order_errors = (
            normalize_orders(
                orders,
                authorization,
                policy,
            )
        )
    else:
        normalized_orders = ()
        orders_valid = False
        order_errors = []
    preflight_valid = bool(
        policy_valid
        and source_valid
        and authorization_valid
        and source_safety_valid
        and input_valid
        and operator_valid
        and orders_valid
    )
    envelope = None
    envelope_valid = False
    envelope_errors: list[str] = []
    if preflight_valid and authorization is not None:
        values: dict[str, Any] = {
            "envelope_id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat(),
            "expires_at": authorization.expires_at,
            "envelope_status": "SEALED",
            "authorization_result_id": (
                authorization_result
                .authorization_result_id
            ),
            "authorization_id": (
                authorization.authorization_id
            ),
            "authorization_hash": (
                authorization.authorization_hash
            ),
            "certificate_id": authorization.certificate_id,
            "preflight_id": authorization.preflight_id,
            "trading_date": authorization.trading_date,
            "operator": envelope_operator.strip(),
            "total_order_count": len(normalized_orders),
            "total_estimated_notional": sum(
                order.estimated_notional
                for order in normalized_orders
            ),
            "orders": normalized_orders,
            "paper_envelope_authorized": True,
            "paper_execution_authorized": False,
            "execution_blocked": True,
            "broker_api_called": False,
            "broker_order_created": False,
            "live_order_created": False,
            "live_execution_authorized": False,
        }
        hash_payload = dict(values)
        hash_payload["orders"] = [
            order.to_dict()
            for order in normalized_orders
        ]
        envelope = AuthorizedPaperRunExecutionEnvelope(
            **values,
            envelope_hash=calculate_envelope_hash(
                hash_payload
            ),
        )
        envelope_valid, _, envelope_errors = (
            verify_execution_envelope(envelope)
        )
    all_checks_passed = bool(
        preflight_valid and envelope_valid
    )
    if all_checks_passed:
        status = "SEALED"
        label = "Authorized Paper Run Execution Envelope 봉인 완료"
        reasons = [
            "Launch Authorization과 Paper Orders가 SHA-256 봉투로 묶였습니다.",
            "봉투 만료 시간은 Launch Authorization과 동일합니다.",
        ]
        next_actions = [
            "Envelope Hash, 주문 요약 및 만료 시간을 검토합니다.",
            "다음 단계에서도 Broker 호출 전 별도 검사가 필요합니다.",
        ]
    elif (
        source_valid
        and authorization_valid
        and source_safety_valid
        and (
            not operator_valid
            or not orders_valid
        )
    ):
        status = "BLOCKED"
        label = "Paper Execution Envelope 생성 차단"
        reasons = [
            "Operator, 확인 문구 또는 Order 검사에 통과하지 못했습니다."
        ]
        next_actions = [
            "BLOCKED 원인을 수정하고 새 봉투를 생성합니다.",
        ]
    else:
        status = "FAILED"
        label = "Paper Execution Envelope 검사 실패"
        reasons = [
            "Source, Authorization, Hash 또는 Safety 검사에 실패했습니다."
        ]
        next_actions = [
            "Warnings를 확인하고 Source를 다시 생성합니다.",
        ]
    return AuthorizedPaperRunExecutionEnvelopeResult(
        version="V12.9",
        created_at=datetime.now().isoformat(),
        envelope_result_id=str(uuid.uuid4()),
        result_status=status,
        result_status_label=label,
        envelope_id=(
            envelope.envelope_id if envelope else None
        ),
        envelope_hash=(
            envelope.envelope_hash if envelope else None
        ),
        expires_at=(
            envelope.expires_at if envelope else None
        ),
        order_count=len(normalized_orders),
        total_estimated_notional=sum(
            order.estimated_notional
            for order in normalized_orders
        ),
        policy_checks_passed=policy_valid,
        input_checks_passed=input_valid,
        source_checks_passed=source_valid,
        authorization_checks_passed=(
            authorization_valid
        ),
        operator_checks_passed=operator_valid,
        order_checks_passed=orders_valid,
        envelope_hash_checks_passed=envelope_valid,
        safety_checks_passed=source_safety_valid,
        all_checks_passed=all_checks_passed,
        paper_envelope_authorized=all_checks_passed,
        paper_execution_authorized=False,
        automatic_execution_authorized=False,
        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,
        envelope_policy=policy,
        envelope=envelope,
        reasons=reasons,
        warnings=[
            *policy_errors,
            *source_errors,
            *operator_errors,
            *order_errors,
            *envelope_errors,
            "V12.9는 실행 요청을 봉인할 뿐 Broker로 전송하지 않습니다.",
            "실제 Broker API, 실제 주문 및 Live Execution은 모두 차단됩니다.",
        ],
        next_actions=next_actions,
    )


def verify_saved_envelope_payload(
    payload: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if payload.get("version") != "V12.9":
        errors.append(
            "저장된 Envelope Version이 V12.9가 아닙니다."
        )
    if payload.get("result_status") not in VALID_ENVELOPE_STATUSES:
        errors.append(
            "저장된 Result Status가 올바르지 않습니다."
        )
    if payload.get("paper_execution_authorized") is not False:
        errors.append(
            "저장된 Envelope가 Paper Execution을 허용합니다."
        )
    if payload.get("execution_blocked") is not True:
        errors.append(
            "저장된 Envelope의 Execution이 차단되지 않았습니다."
        )
    for name in (
        "automatic_execution_authorized",
        "broker_api_called",
        "broker_order_created",
        "live_order_created",
        "live_execution_authorized",
    ):
        if payload.get(name) is not False:
            errors.append(
                f"저장된 {name} 값이 False가 아닙니다."
            )
    return (not errors, errors)


def save_authorized_paper_run_execution_envelope(
    result: AuthorizedPaperRunExecutionEnvelopeResult,
    output_directory: Path | None = None,
) -> AuthorizedPaperRunExecutionEnvelopeResult:
    if not isinstance(
        result,
        AuthorizedPaperRunExecutionEnvelopeResult,
    ):
        raise TypeError(
            "V12.9 Execution Envelope Result 형식이 아닙니다."
        )
    directory = (
        output_directory
        if output_directory is not None
        else AUTHORIZED_PAPER_RUN_EXECUTION_ENVELOPE_OUTPUT_DIRECTORY
    )
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )
    report_path = directory / (
        f"authorized_paper_run_execution_envelope_{timestamp}.json"
    )
    latest_path = directory / (
        "authorized_paper_run_execution_envelope_latest.json"
    )
    payload = result.to_dict()
    write_json_file(report_path, payload)
    write_json_file(latest_path, payload)
    result.report_path = str(report_path)
    result.latest_path = str(latest_path)
    return result


def load_latest_authorized_paper_run_execution_envelope(
    output_directory: Path | None = None,
) -> dict[str, Any]:
    directory = (
        output_directory
        if output_directory is not None
        else AUTHORIZED_PAPER_RUN_EXECUTION_ENVELOPE_OUTPUT_DIRECTORY
    )
    return read_json_file(
        directory
        / "authorized_paper_run_execution_envelope_latest.json"
    )


def print_authorized_paper_run_execution_envelope(
    result: AuthorizedPaperRunExecutionEnvelopeResult,
) -> None:
    line = "=" * 100
    print()
    print(line)
    print("V12.9 AUTHORIZED PAPER RUN EXECUTION ENVELOPE")
    print(line)
    print(f"Result status          : {result.result_status}")
    print(f"Envelope ID            : {result.envelope_id}")
    print(f"Order count            : {result.order_count}")
    print(f"Estimated notional     : ${result.total_estimated_notional:,.2f}")
    print(f"Paper envelope         : {result.paper_envelope_authorized}")
    print(f"Paper execution        : {result.paper_execution_authorized}")
    print(line)
    print(
        "주의: 실행 봉투 생성 단계이며 Broker 전송은 차단됩니다."
    )

