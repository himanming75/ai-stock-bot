import json
import math
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_execution_request_builder import (
    PaperExecutionRequestResult,
    run_paper_execution_request_builder,
    save_paper_execution_request,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_BROKER_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_broker"
)


VALID_FILL_STATUSES = {
    "FILLED",
    "REJECTED",
    "DUPLICATE",
    "BLOCKED",
    "NO_ACTION",
    "FAILED",
}


VALID_FILL_ACTIONS = {
    "PAPER_BUY_FILL",
    "PAPER_SELL_FILL",
    "NO_FILL",
    "BLOCKED",
}


VALID_SIDES = {
    "BUY",
    "SELL",
}


@dataclass(frozen=True)
class PaperBrokerPolicy:
    """
    V9.8 Paper Broker Simulator 정책입니다.

    실제 주문을 전송하지 않고,
    연구용 가상 체결만 계산합니다.
    """

    commission_per_order: float = 0.0
    slippage_percent: float = 0.05

    minimum_quantity: int = 1
    maximum_quantity: int = 100_000

    minimum_fill_price: float = 0.01
    maximum_order_value: float = 1_000_000.0

    allow_market_orders: bool = True
    allow_buy: bool = True
    allow_sell: bool = True

    reject_duplicate_requests: bool = True
    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperBrokerFillResult:
    """
    V9.8 Paper Broker Simulator 결과입니다.
    """

    version: str
    symbol: str
    created_at: str

    fill_id: str
    request_id: str
    idempotency_key: str

    source_request_file: str | None

    fill_status: str
    fill_status_label: str
    fill_action: str
    fill_action_label: str

    side: str
    requested_quantity: int
    filled_quantity: int
    unfilled_quantity: int

    order_type: str
    time_in_force: str

    reference_price: float
    slippage_percent: float
    slippage_per_share: float
    fill_price: float

    gross_fill_value: float
    commission: float
    total_cash_effect: float

    request_ready: bool
    request_authorized: bool
    request_pending: bool

    source_loaded: bool
    source_valid: bool
    request_checks_passed: bool
    policy_checks_passed: bool
    duplicate_checks_passed: bool
    fill_calculation_passed: bool
    fill_generated: bool
    all_checks_passed: bool

    paper_fill_created: bool

    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    execution_simulated: bool
    actual_execution_blocked: bool

    paper_broker_policy: PaperBrokerPolicy

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["paper_broker_policy"] = (
            self.paper_broker_policy.to_dict()
        )

        return payload


def normalize_symbol(
    symbol: str,
) -> str:
    """
    종목 코드를 대문자로 정규화합니다.
    """

    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    return normalized


def is_valid_number(
    value: Any,
) -> bool:
    """
    값이 유효하고 유한한 숫자인지 검사합니다.
    """

    if isinstance(
        value,
        bool,
    ):
        return False

    try:
        numeric_value = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    return math.isfinite(
        numeric_value
    )


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    JSON 파일을 임시 파일 방식으로 안전하게 저장합니다.
    """

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = file_path.with_suffix(
        file_path.suffix + ".tmp"
    )

    with temporary_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    temporary_path.replace(
        file_path
    )


def validate_paper_broker_policy(
    policy: PaperBrokerPolicy,
) -> tuple[
    bool,
    list[str],
]:
    """
    Paper Broker 정책을 검사합니다.
    """

    errors: list[str] = []

    if not is_valid_number(
        policy.commission_per_order
    ):
        errors.append(
            "Commission Per Order가 유효한 숫자가 아닙니다."
        )

    elif policy.commission_per_order < 0:
        errors.append(
            "Commission Per Order가 음수입니다."
        )

    if not is_valid_number(
        policy.slippage_percent
    ):
        errors.append(
            "Slippage Percent가 유효한 숫자가 아닙니다."
        )

    elif not (
        0.0
        <= policy.slippage_percent
        <= 5.0
    ):
        errors.append(
            "Slippage Percent가 허용 범위를 벗어났습니다."
        )

    if not (
        1
        <= policy.minimum_quantity
        <= policy.maximum_quantity
    ):
        errors.append(
            "Minimum Quantity와 Maximum Quantity가 "
            "올바르지 않습니다."
        )

    if not is_valid_number(
        policy.minimum_fill_price
    ):
        errors.append(
            "Minimum Fill Price가 유효한 숫자가 아닙니다."
        )

    elif policy.minimum_fill_price <= 0:
        errors.append(
            "Minimum Fill Price가 0 이하입니다."
        )

    if not is_valid_number(
        policy.maximum_order_value
    ):
        errors.append(
            "Maximum Order Value가 유효한 숫자가 아닙니다."
        )

    elif policy.maximum_order_value <= 0:
        errors.append(
            "Maximum Order Value가 0 이하입니다."
        )

    boolean_fields = {
        "allow_market_orders": (
            policy.allow_market_orders
        ),
        "allow_buy": policy.allow_buy,
        "allow_sell": policy.allow_sell,
        "reject_duplicate_requests": (
            policy.reject_duplicate_requests
        ),
        "paper_only": policy.paper_only,
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }

    for field_name, value in boolean_fields.items():
        if not isinstance(
            value,
            bool,
        ):
            errors.append(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    if not policy.paper_only:
        errors.append(
            "V9.8에서는 Paper Only가 반드시 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V9.8에서는 Live Execution Disabled가 "
            "반드시 True여야 합니다."
        )

    return (
        not errors,
        errors,
    )


def validate_execution_request(
    request: PaperExecutionRequestResult,
) -> tuple[
    bool,
    list[str],
]:
    """
    V9.7 Paper Execution Request를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        request,
        PaperExecutionRequestResult,
    ):
        errors.append(
            "Paper Execution Request 형식이 올바르지 않습니다."
        )

        return (
            False,
            errors,
        )

    if request.version != "V9.7":
        errors.append(
            "Paper Execution Request 버전이 V9.7이 아닙니다."
        )

    if not request.symbol:
        errors.append(
            "Request Symbol이 비어 있습니다."
        )

    if request.request_status != "READY_FOR_PAPER":
        errors.append(
            "Request Status가 READY_FOR_PAPER가 아닙니다."
        )

    if request.request_action not in {
        "PAPER_BUY",
        "PAPER_SELL",
    }:
        errors.append(
            "Request Action이 PAPER_BUY 또는 "
            "PAPER_SELL이 아닙니다."
        )

    if request.side not in VALID_SIDES:
        errors.append(
            f"올바르지 않은 Side입니다: {request.side}"
        )

    if not isinstance(
        request.quantity,
        int,
    ):
        errors.append(
            "Request Quantity가 int 형식이 아닙니다."
        )

    elif request.quantity <= 0:
        errors.append(
            "Request Quantity가 0 이하입니다."
        )

    if not is_valid_number(
        request.reference_price
    ):
        errors.append(
            "Reference Price가 유효한 숫자가 아닙니다."
        )

    elif request.reference_price <= 0:
        errors.append(
            "Reference Price가 0 이하입니다."
        )

    if not is_valid_number(
        request.estimated_order_value
    ):
        errors.append(
            "Estimated Order Value가 유효한 숫자가 아닙니다."
        )

    elif request.estimated_order_value <= 0:
        errors.append(
            "Estimated Order Value가 0 이하입니다."
        )

    expected_value = round(
        request.quantity
        * request.reference_price,
        2,
    )

    if abs(
        request.estimated_order_value
        - expected_value
    ) > 0.01:
        errors.append(
            "Estimated Order Value가 Quantity × "
            "Reference Price와 일치하지 않습니다."
        )

    if request.order_type != "MARKET":
        errors.append(
            "V9.8 기본 Simulator는 MARKET 주문만 지원합니다."
        )

    if not request.paper_execution_authorized:
        errors.append(
            "Paper Execution Authorized가 False입니다."
        )

    if not request.paper_execution_requested:
        errors.append(
            "Paper Execution Requested가 False입니다."
        )

    if not request.paper_execution_pending:
        errors.append(
            "Paper Execution Pending이 False입니다."
        )

    if request.paper_fill_created:
        errors.append(
            "V9.7 단계에서 이미 Paper Fill이 생성되었습니다."
        )

    if request.live_execution_authorized:
        errors.append(
            "Live Execution Authorized가 True입니다."
        )

    if request.broker_order_created:
        errors.append(
            "Broker Order가 이미 생성되었습니다."
        )

    if request.live_order_created:
        errors.append(
            "Live Order가 이미 생성되었습니다."
        )

    if not request.execution_blocked:
        errors.append(
            "실제 Execution이 차단되지 않았습니다."
        )

    if not request.all_checks_passed:
        errors.append(
            "V9.7 검사가 모두 통과되지 않았습니다."
        )

    if not request.request_id:
        errors.append(
            "Request ID가 비어 있습니다."
        )

    if not request.idempotency_key:
        errors.append(
            "Idempotency Key가 비어 있습니다."
        )

    return (
        not errors,
        errors,
    )


def validate_request_against_policy(
    request: PaperExecutionRequestResult,
    policy: PaperBrokerPolicy,
) -> tuple[
    bool,
    list[str],
]:
    """
    요청이 Paper Broker 정책에 맞는지 검사합니다.
    """

    errors: list[str] = []

    if request.side == "BUY":
        if not policy.allow_buy:
            errors.append(
                "Paper Broker Policy에서 BUY가 허용되지 않습니다."
            )

    elif request.side == "SELL":
        if not policy.allow_sell:
            errors.append(
                "Paper Broker Policy에서 SELL이 허용되지 않습니다."
            )

    if request.order_type == "MARKET":
        if not policy.allow_market_orders:
            errors.append(
                "Paper Broker Policy에서 MARKET 주문이 "
                "허용되지 않습니다."
            )

    if not (
        policy.minimum_quantity
        <= request.quantity
        <= policy.maximum_quantity
    ):
        errors.append(
            "Request Quantity가 Policy 범위를 벗어났습니다."
        )

    if (
        request.estimated_order_value
        > policy.maximum_order_value
    ):
        errors.append(
            "Estimated Order Value가 Policy 최대 금액을 "
            "초과했습니다."
        )

    return (
        not errors,
        errors,
    )


def calculate_fill_price(
    side: str,
    reference_price: float,
    slippage_percent: float,
) -> tuple[
    float,
    float,
]:
    """
    Side에 따라 Slippage를 적용한 가상 체결가격을 계산합니다.

    BUY:
        기준가격보다 높은 가격에 체결

    SELL:
        기준가격보다 낮은 가격에 체결
    """

    slippage_rate = (
        slippage_percent
        / 100.0
    )

    slippage_per_share = round(
        reference_price
        * slippage_rate,
        4,
    )

    if side == "BUY":
        fill_price = (
            reference_price
            + slippage_per_share
        )

    elif side == "SELL":
        fill_price = (
            reference_price
            - slippage_per_share
        )

    else:
        raise ValueError(
            f"올바르지 않은 Side입니다: {side}"
        )

    fill_price = round(
        fill_price,
        4,
    )

    return (
        fill_price,
        slippage_per_share,
    )


def calculate_cash_effect(
    side: str,
    quantity: int,
    fill_price: float,
    commission: float,
) -> tuple[
    float,
    float,
]:
    """
    가상 체결금액과 현금 변동액을 계산합니다.

    BUY:
        현금 감소이므로 음수

    SELL:
        현금 증가이므로 양수
    """

    gross_fill_value = round(
        quantity
        * fill_price,
        2,
    )

    if side == "BUY":
        total_cash_effect = -round(
            gross_fill_value
            + commission,
            2,
        )

    elif side == "SELL":
        total_cash_effect = round(
            gross_fill_value
            - commission,
            2,
        )

    else:
        raise ValueError(
            f"올바르지 않은 Side입니다: {side}"
        )

    return (
        gross_fill_value,
        total_cash_effect,
    )


def check_duplicate_request(
    idempotency_key: str,
    processed_idempotency_keys: set[str] | None,
) -> bool:
    """
    Idempotency Key가 이미 처리되었는지 검사합니다.
    """

    if processed_idempotency_keys is None:
        return False

    return (
        idempotency_key
        in processed_idempotency_keys
    )


def determine_fill_decision(
    request_valid: bool,
    policy_valid: bool,
    duplicate_request: bool,
    reject_duplicate_requests: bool,
    request: PaperExecutionRequestResult,
) -> tuple[
    str,
    str,
    str,
    str,
    bool,
    list[str],
]:
    """
    Paper Broker의 체결 여부를 결정합니다.
    """

    if not request_valid:
        return (
            "FAILED",
            "요청 검사 실패",
            "BLOCKED",
            "체결 생성 실패",
            False,
            [
                "V9.7 Paper Execution Request가 유효하지 않습니다.",
                "가상 체결을 생성하지 않습니다.",
            ],
        )

    if not policy_valid:
        return (
            "BLOCKED",
            "Paper Broker 정책 검사 실패",
            "BLOCKED",
            "정책에 의해 체결 차단",
            False,
            [
                "Paper Broker Policy 검사가 통과되지 않았습니다.",
                "가상 체결을 생성하지 않습니다.",
            ],
        )

    if (
        duplicate_request
        and reject_duplicate_requests
    ):
        return (
            "DUPLICATE",
            "중복 요청 감지",
            "NO_FILL",
            "중복 요청 체결 없음",
            False,
            [
                "동일한 Idempotency Key가 이미 처리되었습니다.",
                "중복 가상 체결을 생성하지 않습니다.",
            ],
        )

    if request.request_status != "READY_FOR_PAPER":
        return (
            "NO_ACTION",
            "체결 가능한 요청 없음",
            "NO_FILL",
            "체결 없음",
            False,
            [
                "Request Status가 READY_FOR_PAPER가 아닙니다.",
            ],
        )

    if request.side == "BUY":
        return (
            "FILLED",
            "Paper 매수 체결 완료",
            "PAPER_BUY_FILL",
            "가상 매수 체결",
            True,
            [
                "Paper BUY 요청이 가상 체결되었습니다.",
                "실제 Broker에는 주문을 전송하지 않았습니다.",
            ],
        )

    if request.side == "SELL":
        return (
            "FILLED",
            "Paper 매도 체결 완료",
            "PAPER_SELL_FILL",
            "가상 매도 체결",
            True,
            [
                "Paper SELL 요청이 가상 체결되었습니다.",
                "실제 Broker에는 주문을 전송하지 않았습니다.",
            ],
        )

    return (
        "NO_ACTION",
        "체결할 Side 없음",
        "NO_FILL",
        "체결 없음",
        False,
        [
            "BUY 또는 SELL Side가 없습니다.",
        ],
    )


def build_fill_notes(
    fill_status: str,
    request_errors: list[str],
    policy_errors: list[str],
) -> tuple[
    list[str],
    list[str],
]:
    """
    경고와 다음 단계를 생성합니다.
    """

    warnings: list[str] = []

    warnings.extend(
        request_errors
    )

    warnings.extend(
        policy_errors
    )

    warnings.extend(
        [
            (
                "이 체결은 연구용 Paper Trading "
                "시뮬레이션 결과입니다."
            ),
            (
                "실제 Broker API 또는 실계좌 API는 "
                "호출되지 않았습니다."
            ),
            (
                "시장가 체결가격은 실제 시장 체결이 아니라 "
                "설정된 Slippage를 사용한 계산값입니다."
            ),
            (
                "Live Execution은 항상 차단됩니다."
            ),
        ]
    )

    if fill_status == "FILLED":
        next_actions = [
            (
                "V9.9 Paper Portfolio Manager에 "
                "가상 체결 결과를 전달합니다."
            ),
            (
                "가상 현금과 보유 수량을 업데이트합니다."
            ),
            (
                "평균 매입가격과 미실현 손익을 계산합니다."
            ),
            (
                "Idempotency Key를 처리 완료 목록에 기록합니다."
            ),
        ]

    elif fill_status == "DUPLICATE":
        next_actions = [
            (
                "기존 처리 결과를 확인합니다."
            ),
            (
                "중복 요청을 다시 체결하지 않습니다."
            ),
        ]

    elif fill_status == "BLOCKED":
        next_actions = [
            (
                "Paper Broker Policy 설정을 확인합니다."
            ),
            (
                "정책 검사가 통과되기 전 체결하지 않습니다."
            ),
        ]

    else:
        next_actions = [
            (
                "Paper Execution Request의 상태와 필수값을 "
                "확인합니다."
            ),
            (
                "문제를 수정한 후 새 요청을 생성합니다."
            ),
        ]

    return (
        warnings,
        next_actions,
    )


def run_paper_broker_simulator(
    symbol: str = "AAPL",
    request: PaperExecutionRequestResult | None = None,
    broker_policy: PaperBrokerPolicy | None = None,
    processed_idempotency_keys: set[str] | None = None,
    account_cash: float = 10_000.0,
) -> PaperBrokerFillResult:
    """
    V9.7 Paper Execution Request를 가상 체결합니다.

    실제 Broker API, 실제 주문 또는 실계좌 작업은
    수행하지 않습니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    policy = (
        broker_policy
        if broker_policy is not None
        else PaperBrokerPolicy()
    )

    (
        policy_valid,
        policy_errors,
    ) = validate_paper_broker_policy(
        policy
    )

    if request is None:
        request = run_paper_execution_request_builder(
            symbol=normalized_symbol,
            account_cash=account_cash,
        )

        save_paper_execution_request(
            request
        )

    if request.symbol != normalized_symbol:
        raise ValueError(
            "Paper Execution Request Symbol과 "
            "요청 Symbol이 일치하지 않습니다."
        )

    (
        request_valid,
        request_errors,
    ) = validate_execution_request(
        request
    )

    (
        request_policy_valid,
        request_policy_errors,
    ) = validate_request_against_policy(
        request=request,
        policy=policy,
    )

    policy_errors.extend(
        request_policy_errors
    )

    policy_checks_passed = (
        policy_valid
        and request_policy_valid
    )

    duplicate_request = check_duplicate_request(
        idempotency_key=request.idempotency_key,
        processed_idempotency_keys=(
            processed_idempotency_keys
        ),
    )

    duplicate_checks_passed = (
        not duplicate_request
        or not policy.reject_duplicate_requests
    )

    (
        fill_status,
        fill_status_label,
        fill_action,
        fill_action_label,
        fill_generated,
        decision_reasons,
    ) = determine_fill_decision(
        request_valid=request_valid,
        policy_valid=policy_checks_passed,
        duplicate_request=duplicate_request,
        reject_duplicate_requests=(
            policy.reject_duplicate_requests
        ),
        request=request,
    )

    filled_quantity = 0
    unfilled_quantity = int(
        request.quantity
    )

    fill_price = 0.0
    slippage_per_share = 0.0
    gross_fill_value = 0.0
    total_cash_effect = 0.0

    commission = round(
        float(
            policy.commission_per_order
        ),
        2,
    )

    fill_calculation_passed = False

    if fill_generated:
        (
            fill_price,
            slippage_per_share,
        ) = calculate_fill_price(
            side=request.side,
            reference_price=float(
                request.reference_price
            ),
            slippage_percent=float(
                policy.slippage_percent
            ),
        )

        if fill_price < policy.minimum_fill_price:
            fill_status = "BLOCKED"
            fill_status_label = (
                "계산된 체결가격이 최소가격 미만"
            )
            fill_action = "BLOCKED"
            fill_action_label = (
                "체결가격 검사 실패"
            )
            fill_generated = False

            policy_errors.append(
                "계산된 Fill Price가 Minimum Fill Price보다 "
                "낮습니다."
            )

        else:
            filled_quantity = int(
                request.quantity
            )

            unfilled_quantity = (
                request.quantity
                - filled_quantity
            )

            (
                gross_fill_value,
                total_cash_effect,
            ) = calculate_cash_effect(
                side=request.side,
                quantity=filled_quantity,
                fill_price=fill_price,
                commission=commission,
            )

            fill_calculation_passed = (
                filled_quantity > 0
                and unfilled_quantity == 0
                and fill_price > 0
                and gross_fill_value > 0
                and is_valid_number(
                    total_cash_effect
                )
            )

    paper_fill_created = (
        fill_status == "FILLED"
        and fill_generated
        and fill_calculation_passed
    )

    all_checks_passed = (
        request_valid
        and policy_checks_passed
        and duplicate_checks_passed
        and fill_calculation_passed
        and paper_fill_created
    )

    fill_id = str(
        uuid.uuid4()
    )

    reasons: list[str] = []

    reasons.extend(
        decision_reasons
    )

    reasons.extend(
        [
            (
                f"요청 Side는 {request.side}입니다."
            ),
            (
                f"요청 수량은 {request.quantity}주입니다."
            ),
            (
                f"Reference Price는 "
                f"${request.reference_price:,.4f}입니다."
            ),
            (
                f"적용 Slippage는 "
                f"{policy.slippage_percent:.4f}%입니다."
            ),
            (
                f"가상 Commission은 "
                f"${commission:,.2f}입니다."
            ),
        ]
    )

    if paper_fill_created:
        reasons.extend(
            [
                (
                    f"가상 체결가격은 "
                    f"${fill_price:,.4f}입니다."
                ),
                (
                    f"가상 체결금액은 "
                    f"${gross_fill_value:,.2f}입니다."
                ),
                (
                    f"가상 현금 변동액은 "
                    f"${total_cash_effect:,.2f}입니다."
                ),
            ]
        )

    (
        warnings,
        next_actions,
    ) = build_fill_notes(
        fill_status=fill_status,
        request_errors=request_errors,
        policy_errors=policy_errors,
    )

    result = PaperBrokerFillResult(
        version="V9.8",
        symbol=normalized_symbol,
        created_at=datetime.now().isoformat(),

        fill_id=fill_id,
        request_id=request.request_id,
        idempotency_key=request.idempotency_key,

        source_request_file=(
            request.latest_path
            or request.report_path
            or request.source_manual_approval_file
        ),

        fill_status=fill_status,
        fill_status_label=(
            fill_status_label
        ),
        fill_action=fill_action,
        fill_action_label=(
            fill_action_label
        ),

        side=request.side,
        requested_quantity=int(
            request.quantity
        ),
        filled_quantity=int(
            filled_quantity
        ),
        unfilled_quantity=int(
            unfilled_quantity
        ),

        order_type=request.order_type,
        time_in_force=request.time_in_force,

        reference_price=float(
            request.reference_price
        ),
        slippage_percent=float(
            policy.slippage_percent
        ),
        slippage_per_share=float(
            slippage_per_share
        ),
        fill_price=float(
            fill_price
        ),

        gross_fill_value=float(
            gross_fill_value
        ),
        commission=float(
            commission
        ),
        total_cash_effect=float(
            total_cash_effect
        ),

        request_ready=(
            request.request_status
            == "READY_FOR_PAPER"
        ),
        request_authorized=(
            request.paper_execution_authorized
        ),
        request_pending=(
            request.paper_execution_pending
        ),

        source_loaded=True,
        source_valid=request_valid,
        request_checks_passed=(
            request_valid
        ),
        policy_checks_passed=(
            policy_checks_passed
        ),
        duplicate_checks_passed=(
            duplicate_checks_passed
        ),
        fill_calculation_passed=(
            fill_calculation_passed
        ),
        fill_generated=(
            fill_generated
        ),
        all_checks_passed=(
            all_checks_passed
        ),

        paper_fill_created=(
            paper_fill_created
        ),

        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,

        execution_simulated=(
            paper_fill_created
        ),
        actual_execution_blocked=True,

        paper_broker_policy=policy,

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_broker_fill(
        result
    )

    return result


def save_paper_broker_fill(
    result: PaperBrokerFillResult,
) -> tuple[
    Path,
    Path,
]:
    """
    V9.8 Paper Broker 결과를 JSON으로 저장합니다.
    """

    PAPER_BROKER_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        PAPER_BROKER_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "paper_broker_fill_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        PAPER_BROKER_OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_"
            "paper_broker_fill_latest.json"
        )
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

    payload = result.to_dict()

    write_json_file(
        report_path,
        payload,
    )

    write_json_file(
        latest_path,
        payload,
    )

    return (
        report_path,
        latest_path,
    )


def print_paper_broker_fill(
    result: PaperBrokerFillResult,
) -> None:
    """
    V9.8 Paper Broker 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        f"{result.symbol} V9.8 "
        "PAPER BROKER SIMULATOR"
    )
    print("=" * 140)

    print(
        f"Fill status                    : "
        f"{result.fill_status}"
    )

    print(
        f"Fill status label              : "
        f"{result.fill_status_label}"
    )

    print(
        f"Fill action                    : "
        f"{result.fill_action}"
    )

    print(
        f"Fill action label              : "
        f"{result.fill_action_label}"
    )

    print(
        f"Fill ID                        : "
        f"{result.fill_id}"
    )

    print(
        f"Request ID                     : "
        f"{result.request_id}"
    )

    print(
        f"Idempotency key                : "
        f"{result.idempotency_key}"
    )

    print()
    print("PAPER FILL")
    print("-" * 140)

    print(
        f"Side                           : "
        f"{result.side}"
    )

    print(
        f"Requested quantity             : "
        f"{result.requested_quantity}"
    )

    print(
        f"Filled quantity                : "
        f"{result.filled_quantity}"
    )

    print(
        f"Unfilled quantity              : "
        f"{result.unfilled_quantity}"
    )

    print(
        f"Reference price                : "
        f"${result.reference_price:,.4f}"
    )

    print(
        f"Slippage percent               : "
        f"{result.slippage_percent:.4f}%"
    )

    print(
        f"Slippage per share             : "
        f"${result.slippage_per_share:,.4f}"
    )

    print(
        f"Fill price                     : "
        f"${result.fill_price:,.4f}"
    )

    print(
        f"Gross fill value               : "
        f"${result.gross_fill_value:,.2f}"
    )

    print(
        f"Commission                     : "
        f"${result.commission:,.2f}"
    )

    print(
        f"Total cash effect              : "
        f"${result.total_cash_effect:,.2f}"
    )

    print()
    print("REQUEST STATUS")
    print("-" * 140)

    print(
        f"Request ready                  : "
        f"{result.request_ready}"
    )

    print(
        f"Request authorized             : "
        f"{result.request_authorized}"
    )

    print(
        f"Request pending                : "
        f"{result.request_pending}"
    )

    print()
    print("VALIDATION")
    print("-" * 140)

    print(
        f"Source loaded                  : "
        f"{result.source_loaded}"
    )

    print(
        f"Source valid                   : "
        f"{result.source_valid}"
    )

    print(
        f"Request checks passed          : "
        f"{result.request_checks_passed}"
    )

    print(
        f"Policy checks passed           : "
        f"{result.policy_checks_passed}"
    )

    print(
        f"Duplicate checks passed        : "
        f"{result.duplicate_checks_passed}"
    )

    print(
        f"Fill calculation passed        : "
        f"{result.fill_calculation_passed}"
    )

    print(
        f"Fill generated                 : "
        f"{result.fill_generated}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * 140)

    print(
        f"Paper fill created             : "
        f"{result.paper_fill_created}"
    )

    print(
        f"Execution simulated            : "
        f"{result.execution_simulated}"
    )

    print(
        f"Broker API called              : "
        f"{result.broker_api_called}"
    )

    print(
        f"Broker order created           : "
        f"{result.broker_order_created}"
    )

    print(
        f"Live order created             : "
        f"{result.live_order_created}"
    )

    print(
        f"Live execution authorized      : "
        f"{result.live_execution_authorized}"
    )

    print(
        f"Actual execution blocked       : "
        f"{result.actual_execution_blocked}"
    )

    if result.reasons:
        print()
        print("REASONS")
        print("-" * 140)

        for reason in result.reasons:
            print(
                f"- {reason}"
            )

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * 140)

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * 140)

        for action in result.next_actions:
            print(
                f"- {action}"
            )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Source Request file            : "
        f"{result.source_request_file}"
    )

    print(
        f"Report file                    : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                    : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print("=" * 140)

    print(
        "주의: 이 결과는 연구용 가상 체결입니다. "
        "실제 Broker API, 실제 계좌, 실제 주문 또는 "
        "실거래 체결과는 연결되지 않습니다."
    )