import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

from backtest.paper_broker_simulator import (
    VALID_FILL_ACTIONS,
    VALID_FILL_STATUSES,
    VALID_SIDES,
    PaperBrokerFillResult,
    PaperBrokerPolicy,
    calculate_cash_effect,
    calculate_fill_price,
    check_duplicate_request,
    determine_fill_decision,
    run_paper_broker_simulator,
    save_paper_broker_fill,
    validate_execution_request,
    validate_paper_broker_policy,
    validate_request_against_policy,
)
from backtest.paper_execution_request_builder import (
    PaperExecutionPolicy,
    PaperExecutionRequestResult,
    run_paper_execution_request_builder,
    save_paper_execution_request,
)


def print_header() -> None:
    """
    V9.8 테스트 제목을 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "AI STOCK BOT V9.8 "
        "PAPER BROKER SIMULATOR TEST"
    )
    print("=" * 140)


def print_check(
    name: str,
    value: bool,
) -> None:
    """
    검증 결과를 True 또는 False로 출력합니다.
    """

    print(
        f"{name:<52}: {value}"
    )


def load_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽어 Dictionary로 반환합니다.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"JSON 파일이 없습니다: {file_path}"
        )

    if file_path.stat().st_size <= 0:
        raise RuntimeError(
            f"JSON 파일이 비어 있습니다: {file_path}"
        )

    with file_path.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            "JSON 최상위 데이터가 Dictionary가 아닙니다."
        )

    return payload


def validate_request_result(
    request: PaperExecutionRequestResult,
) -> None:
    """
    V9.7 Paper Execution Request 기본 구조를 검사합니다.
    """

    if not isinstance(
        request,
        PaperExecutionRequestResult,
    ):
        raise RuntimeError(
            "Request가 PaperExecutionRequestResult "
            "형식이 아닙니다."
        )

    if request.version != "V9.7":
        raise RuntimeError(
            f"Request 버전이 V9.7이 아닙니다: "
            f"{request.version}"
        )

    if request.request_status != "READY_FOR_PAPER":
        raise RuntimeError(
            "Request Status가 READY_FOR_PAPER가 아닙니다."
        )

    if request.request_action not in {
        "PAPER_BUY",
        "PAPER_SELL",
    }:
        raise RuntimeError(
            "Request Action이 PAPER_BUY 또는 "
            "PAPER_SELL이 아닙니다."
        )

    if request.side not in VALID_SIDES:
        raise RuntimeError(
            f"Request Side가 올바르지 않습니다: "
            f"{request.side}"
        )

    if not isinstance(
        request.quantity,
        int,
    ):
        raise RuntimeError(
            "Request Quantity가 int 형식이 아닙니다."
        )

    if request.quantity <= 0:
        raise RuntimeError(
            "Request Quantity가 0 이하입니다."
        )

    if request.reference_price <= 0:
        raise RuntimeError(
            "Request Reference Price가 0 이하입니다."
        )

    if request.estimated_order_value <= 0:
        raise RuntimeError(
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
        raise RuntimeError(
            "Request Estimated Order Value 계산이 "
            "일치하지 않습니다."
        )

    if request.order_type != "MARKET":
        raise RuntimeError(
            "V9.8 테스트용 Request가 MARKET 주문이 아닙니다."
        )

    if not request.paper_execution_authorized:
        raise RuntimeError(
            "Paper Execution Authorized가 False입니다."
        )

    if not request.paper_execution_requested:
        raise RuntimeError(
            "Paper Execution Requested가 False입니다."
        )

    if not request.paper_execution_pending:
        raise RuntimeError(
            "Paper Execution Pending이 False입니다."
        )

    if request.paper_fill_created:
        raise RuntimeError(
            "V9.7 단계에서 이미 Paper Fill이 생성되었습니다."
        )

    if request.live_execution_authorized:
        raise RuntimeError(
            "V9.7에서 Live Execution이 허용되었습니다."
        )

    if request.broker_order_created:
        raise RuntimeError(
            "V9.7에서 Broker Order가 생성되었습니다."
        )

    if request.live_order_created:
        raise RuntimeError(
            "V9.7에서 Live Order가 생성되었습니다."
        )

    if not request.execution_blocked:
        raise RuntimeError(
            "V9.7에서 실제 Execution이 차단되지 않았습니다."
        )

    if not request.all_checks_passed:
        raise RuntimeError(
            "V9.7 검사가 모두 통과되지 않았습니다."
        )

    if not request.request_id:
        raise RuntimeError(
            "Request ID가 비어 있습니다."
        )

    if not request.idempotency_key:
        raise RuntimeError(
            "Idempotency Key가 비어 있습니다."
        )

    (
        request_valid,
        request_errors,
    ) = validate_execution_request(
        request
    )

    if not request_valid:
        raise RuntimeError(
            "정상 V9.7 Request가 V9.8 Source 검사에 "
            "실패했습니다: "
            f"{request_errors}"
        )

    if request_errors:
        raise RuntimeError(
            "정상 V9.7 Request 검사에서 "
            "오류 메시지가 생성되었습니다."
        )


def validate_policy_structure(
    policy: PaperBrokerPolicy,
) -> None:
    """
    PaperBrokerPolicy 구조와 자료형을 검사합니다.
    """

    if not isinstance(
        policy,
        PaperBrokerPolicy,
    ):
        raise RuntimeError(
            "Paper Broker Policy 형식이 올바르지 않습니다."
        )

    numeric_fields = {
        "commission_per_order": (
            policy.commission_per_order
        ),
        "slippage_percent": (
            policy.slippage_percent
        ),
        "minimum_fill_price": (
            policy.minimum_fill_price
        ),
        "maximum_order_value": (
            policy.maximum_order_value
        ),
    }

    for field_name, value in numeric_fields.items():
        if not isinstance(
            value,
            float,
        ):
            raise RuntimeError(
                f"{field_name}가 float 형식이 아닙니다."
            )

    integer_fields = {
        "minimum_quantity": (
            policy.minimum_quantity
        ),
        "maximum_quantity": (
            policy.maximum_quantity
        ),
    }

    for field_name, value in integer_fields.items():
        if not isinstance(
            value,
            int,
        ):
            raise RuntimeError(
                f"{field_name}가 int 형식이 아닙니다."
            )

    boolean_fields = {
        "allow_market_orders": (
            policy.allow_market_orders
        ),
        "allow_buy": (
            policy.allow_buy
        ),
        "allow_sell": (
            policy.allow_sell
        ),
        "reject_duplicate_requests": (
            policy.reject_duplicate_requests
        ),
        "paper_only": (
            policy.paper_only
        ),
        "live_execution_disabled": (
            policy.live_execution_disabled
        ),
    }

    for field_name, value in boolean_fields.items():
        if not isinstance(
            value,
            bool,
        ):
            raise RuntimeError(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    expected_keys = {
        "commission_per_order",
        "slippage_percent",
        "minimum_quantity",
        "maximum_quantity",
        "minimum_fill_price",
        "maximum_order_value",
        "allow_market_orders",
        "allow_buy",
        "allow_sell",
        "reject_duplicate_requests",
        "paper_only",
        "live_execution_disabled",
    }

    actual_keys = set(
        policy.to_dict().keys()
    )

    if actual_keys != expected_keys:
        raise RuntimeError(
            "PaperBrokerPolicy.to_dict() 구조가 "
            "예상 결과와 일치하지 않습니다."
        )


def validate_policy_is_immutable(
    policy: PaperBrokerPolicy,
) -> None:
    """
    PaperBrokerPolicy가 Frozen Dataclass인지 검사합니다.
    """

    original_value = (
        policy.slippage_percent
    )

    immutable = False

    try:
        policy.slippage_percent = 1.0

    except (
        FrozenInstanceError,
        AttributeError,
    ):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "PaperBrokerPolicy 값을 직접 변경할 수 있습니다."
        )

    if (
        policy.slippage_percent
        != original_value
    ):
        raise RuntimeError(
            "불변 PaperBrokerPolicy 값이 변경되었습니다."
        )


def validate_normal_policy(
    policy: PaperBrokerPolicy,
) -> None:
    """
    기본 Paper Broker 정책이 유효한지 검사합니다.
    """

    (
        policy_valid,
        policy_errors,
    ) = validate_paper_broker_policy(
        policy
    )

    if not policy_valid:
        raise RuntimeError(
            "정상 Paper Broker Policy가 검사에 실패했습니다: "
            f"{policy_errors}"
        )

    if policy_errors:
        raise RuntimeError(
            "정상 Policy 검사에서 오류 메시지가 생성되었습니다."
        )


def validate_invalid_policies() -> None:
    """
    잘못된 Paper Broker 정책이 거부되는지 검사합니다.
    """

    invalid_policies = [
        PaperBrokerPolicy(
            commission_per_order=-1.0,
        ),
        PaperBrokerPolicy(
            slippage_percent=-0.1,
        ),
        PaperBrokerPolicy(
            slippage_percent=5.1,
        ),
        PaperBrokerPolicy(
            minimum_quantity=0,
        ),
        PaperBrokerPolicy(
            minimum_quantity=100,
            maximum_quantity=10,
        ),
        PaperBrokerPolicy(
            minimum_fill_price=0.0,
        ),
        PaperBrokerPolicy(
            maximum_order_value=0.0,
        ),
        PaperBrokerPolicy(
            paper_only=False,
        ),
        PaperBrokerPolicy(
            live_execution_disabled=False,
        ),
    ]

    for policy in invalid_policies:
        (
            policy_valid,
            errors,
        ) = validate_paper_broker_policy(
            policy
        )

        if policy_valid:
            raise RuntimeError(
                "잘못된 Paper Broker Policy가 "
                "유효한 것으로 판정되었습니다."
            )

        if not errors:
            raise RuntimeError(
                "잘못된 Policy 검사에서 오류 메시지가 "
                "생성되지 않았습니다."
            )


def validate_request_policy(
    request: PaperExecutionRequestResult,
    policy: PaperBrokerPolicy,
) -> None:
    """
    정상 요청이 Paper Broker Policy를 통과하는지 검사합니다.
    """

    (
        request_valid,
        request_errors,
    ) = validate_request_against_policy(
        request=request,
        policy=policy,
    )

    if not request_valid:
        raise RuntimeError(
            "정상 Request가 Paper Broker Policy를 "
            "통과하지 못했습니다: "
            f"{request_errors}"
        )

    if request_errors:
        raise RuntimeError(
            "정상 Request Policy 검사에서 "
            "오류 메시지가 생성되었습니다."
        )


def validate_fill_price_helpers() -> None:
    """
    BUY와 SELL 체결가격 계산을 검사합니다.
    """

    reference_price = 100.0
    slippage_percent = 0.05

    (
        buy_fill_price,
        buy_slippage,
    ) = calculate_fill_price(
        side="BUY",
        reference_price=reference_price,
        slippage_percent=slippage_percent,
    )

    expected_slippage = 0.05
    expected_buy_price = 100.05

    if abs(
        buy_slippage
        - expected_slippage
    ) > 0.0001:
        raise RuntimeError(
            "BUY Slippage 계산이 일치하지 않습니다."
        )

    if abs(
        buy_fill_price
        - expected_buy_price
    ) > 0.0001:
        raise RuntimeError(
            "BUY Fill Price 계산이 일치하지 않습니다."
        )

    (
        sell_fill_price,
        sell_slippage,
    ) = calculate_fill_price(
        side="SELL",
        reference_price=reference_price,
        slippage_percent=slippage_percent,
    )

    expected_sell_price = 99.95

    if abs(
        sell_slippage
        - expected_slippage
    ) > 0.0001:
        raise RuntimeError(
            "SELL Slippage 계산이 일치하지 않습니다."
        )

    if abs(
        sell_fill_price
        - expected_sell_price
    ) > 0.0001:
        raise RuntimeError(
            "SELL Fill Price 계산이 일치하지 않습니다."
        )

    invalid_side_rejected = False

    try:
        calculate_fill_price(
            side="HOLD",
            reference_price=reference_price,
            slippage_percent=slippage_percent,
        )

    except ValueError:
        invalid_side_rejected = True

    if not invalid_side_rejected:
        raise RuntimeError(
            "잘못된 Fill Price Side가 거부되지 않았습니다."
        )


def validate_cash_effect_helpers() -> None:
    """
    BUY와 SELL 현금 변동 계산을 검사합니다.
    """

    (
        buy_gross_value,
        buy_cash_effect,
    ) = calculate_cash_effect(
        side="BUY",
        quantity=4,
        fill_price=100.0,
        commission=1.0,
    )

    if abs(
        buy_gross_value
        - 400.0
    ) > 0.01:
        raise RuntimeError(
            "BUY Gross Fill Value 계산이 일치하지 않습니다."
        )

    if abs(
        buy_cash_effect
        - (-401.0)
    ) > 0.01:
        raise RuntimeError(
            "BUY Total Cash Effect 계산이 일치하지 않습니다."
        )

    (
        sell_gross_value,
        sell_cash_effect,
    ) = calculate_cash_effect(
        side="SELL",
        quantity=4,
        fill_price=100.0,
        commission=1.0,
    )

    if abs(
        sell_gross_value
        - 400.0
    ) > 0.01:
        raise RuntimeError(
            "SELL Gross Fill Value 계산이 일치하지 않습니다."
        )

    if abs(
        sell_cash_effect
        - 399.0
    ) > 0.01:
        raise RuntimeError(
            "SELL Total Cash Effect 계산이 일치하지 않습니다."
        )

    invalid_side_rejected = False

    try:
        calculate_cash_effect(
            side="HOLD",
            quantity=4,
            fill_price=100.0,
            commission=1.0,
        )

    except ValueError:
        invalid_side_rejected = True

    if not invalid_side_rejected:
        raise RuntimeError(
            "잘못된 Cash Effect Side가 거부되지 않았습니다."
        )


def validate_duplicate_helper(
    request: PaperExecutionRequestResult,
) -> None:
    """
    Duplicate Request Helper를 검사합니다.
    """

    no_processed_keys = check_duplicate_request(
        idempotency_key=request.idempotency_key,
        processed_idempotency_keys=None,
    )

    if no_processed_keys:
        raise RuntimeError(
            "Processed Key Set이 None인데 "
            "Duplicate로 판정되었습니다."
        )

    empty_processed_keys = check_duplicate_request(
        idempotency_key=request.idempotency_key,
        processed_idempotency_keys=set(),
    )

    if empty_processed_keys:
        raise RuntimeError(
            "빈 Processed Key Set에서 Duplicate가 "
            "검출되었습니다."
        )

    processed_keys = {
        request.idempotency_key,
    }

    duplicate_detected = check_duplicate_request(
        idempotency_key=request.idempotency_key,
        processed_idempotency_keys=processed_keys,
    )

    if not duplicate_detected:
        raise RuntimeError(
            "처리된 Idempotency Key가 Duplicate로 "
            "검출되지 않았습니다."
        )


def validate_decision_rules(
    request: PaperExecutionRequestResult,
) -> None:
    """
    Fill Decision 규칙을 직접 검사합니다.
    """

    normal_decision = determine_fill_decision(
        request_valid=True,
        policy_valid=True,
        duplicate_request=False,
        reject_duplicate_requests=True,
        request=request,
    )

    expected_action = (
        "PAPER_BUY_FILL"
        if request.side == "BUY"
        else "PAPER_SELL_FILL"
    )

    if normal_decision[0] != "FILLED":
        raise RuntimeError(
            "정상 요청의 Fill Status가 FILLED가 아닙니다."
        )

    if normal_decision[2] != expected_action:
        raise RuntimeError(
            "정상 요청의 Fill Action이 Side와 "
            "일치하지 않습니다."
        )

    if not normal_decision[4]:
        raise RuntimeError(
            "정상 요청의 Fill Generated가 False입니다."
        )

    failed_decision = determine_fill_decision(
        request_valid=False,
        policy_valid=True,
        duplicate_request=False,
        reject_duplicate_requests=True,
        request=request,
    )

    if failed_decision[0] != "FAILED":
        raise RuntimeError(
            "잘못된 Request의 Fill Status가 FAILED가 아닙니다."
        )

    if failed_decision[2] != "BLOCKED":
        raise RuntimeError(
            "잘못된 Request의 Fill Action이 BLOCKED가 아닙니다."
        )

    if failed_decision[4]:
        raise RuntimeError(
            "잘못된 Request에서 Fill이 생성되었습니다."
        )

    blocked_decision = determine_fill_decision(
        request_valid=True,
        policy_valid=False,
        duplicate_request=False,
        reject_duplicate_requests=True,
        request=request,
    )

    if blocked_decision[0] != "BLOCKED":
        raise RuntimeError(
            "Policy Invalid 상태가 BLOCKED가 아닙니다."
        )

    if blocked_decision[4]:
        raise RuntimeError(
            "Policy Invalid 상태에서 Fill이 생성되었습니다."
        )

    duplicate_decision = determine_fill_decision(
        request_valid=True,
        policy_valid=True,
        duplicate_request=True,
        reject_duplicate_requests=True,
        request=request,
    )

    if duplicate_decision[0] != "DUPLICATE":
        raise RuntimeError(
            "중복 Request의 Fill Status가 DUPLICATE가 아닙니다."
        )

    if duplicate_decision[2] != "NO_FILL":
        raise RuntimeError(
            "중복 Request의 Fill Action이 NO_FILL이 아닙니다."
        )

    if duplicate_decision[4]:
        raise RuntimeError(
            "중복 Request에서 Fill이 생성되었습니다."
        )

    allowed_duplicate_decision = determine_fill_decision(
        request_valid=True,
        policy_valid=True,
        duplicate_request=True,
        reject_duplicate_requests=False,
        request=request,
    )

    if allowed_duplicate_decision[0] != "FILLED":
        raise RuntimeError(
            "중복 허용 정책에서 요청이 FILLED가 아닙니다."
        )

    if not allowed_duplicate_decision[4]:
        raise RuntimeError(
            "중복 허용 정책에서 Fill이 생성되지 않았습니다."
        )


def validate_result_structure(
    result: PaperBrokerFillResult,
) -> None:
    """
    V9.8 PaperBrokerFillResult 구조와 필수값을 검사합니다.
    """

    if not isinstance(
        result,
        PaperBrokerFillResult,
    ):
        raise RuntimeError(
            "결과가 PaperBrokerFillResult 형식이 아닙니다."
        )

    if result.version != "V9.8":
        raise RuntimeError(
            f"버전이 V9.8이 아닙니다: {result.version}"
        )

    if not result.symbol:
        raise RuntimeError(
            "Symbol이 비어 있습니다."
        )

    if result.symbol != result.symbol.upper():
        raise RuntimeError(
            "Symbol이 대문자로 정규화되지 않았습니다."
        )

    if not result.created_at:
        raise RuntimeError(
            "Created At이 비어 있습니다."
        )

    if not result.fill_id:
        raise RuntimeError(
            "Fill ID가 비어 있습니다."
        )

    if not result.request_id:
        raise RuntimeError(
            "Request ID가 비어 있습니다."
        )

    if not result.idempotency_key:
        raise RuntimeError(
            "Idempotency Key가 비어 있습니다."
        )

    if result.fill_status not in VALID_FILL_STATUSES:
        raise RuntimeError(
            "올바르지 않은 Fill Status입니다: "
            f"{result.fill_status}"
        )

    if result.fill_action not in VALID_FILL_ACTIONS:
        raise RuntimeError(
            "올바르지 않은 Fill Action입니다: "
            f"{result.fill_action}"
        )

    if not result.fill_status_label:
        raise RuntimeError(
            "Fill Status Label이 비어 있습니다."
        )

    if not result.fill_action_label:
        raise RuntimeError(
            "Fill Action Label이 비어 있습니다."
        )

    if result.side not in VALID_SIDES:
        raise RuntimeError(
            f"올바르지 않은 Fill Side입니다: "
            f"{result.side}"
        )

    integer_fields = {
        "requested_quantity": (
            result.requested_quantity
        ),
        "filled_quantity": (
            result.filled_quantity
        ),
        "unfilled_quantity": (
            result.unfilled_quantity
        ),
    }

    for field_name, value in integer_fields.items():
        if not isinstance(
            value,
            int,
        ):
            raise RuntimeError(
                f"{field_name}가 int 형식이 아닙니다."
            )

        if value < 0:
            raise RuntimeError(
                f"{field_name}가 음수입니다."
            )

    if (
        result.filled_quantity
        + result.unfilled_quantity
        != result.requested_quantity
    ):
        raise RuntimeError(
            "Filled Quantity와 Unfilled Quantity의 합이 "
            "Requested Quantity와 일치하지 않습니다."
        )

    numeric_fields = {
        "reference_price": (
            result.reference_price
        ),
        "slippage_percent": (
            result.slippage_percent
        ),
        "slippage_per_share": (
            result.slippage_per_share
        ),
        "fill_price": (
            result.fill_price
        ),
        "gross_fill_value": (
            result.gross_fill_value
        ),
        "commission": (
            result.commission
        ),
        "total_cash_effect": (
            result.total_cash_effect
        ),
    }

    for field_name, value in numeric_fields.items():
        if isinstance(
            value,
            bool,
        ):
            raise RuntimeError(
                f"{field_name}가 숫자 형식이 아닙니다."
            )

        if not isinstance(
            value,
            (
                int,
                float,
            ),
        ):
            raise RuntimeError(
                f"{field_name}가 숫자 형식이 아닙니다."
            )

    boolean_fields = {
        "request_ready": (
            result.request_ready
        ),
        "request_authorized": (
            result.request_authorized
        ),
        "request_pending": (
            result.request_pending
        ),
        "source_loaded": (
            result.source_loaded
        ),
        "source_valid": (
            result.source_valid
        ),
        "request_checks_passed": (
            result.request_checks_passed
        ),
        "policy_checks_passed": (
            result.policy_checks_passed
        ),
        "duplicate_checks_passed": (
            result.duplicate_checks_passed
        ),
        "fill_calculation_passed": (
            result.fill_calculation_passed
        ),
        "fill_generated": (
            result.fill_generated
        ),
        "all_checks_passed": (
            result.all_checks_passed
        ),
        "paper_fill_created": (
            result.paper_fill_created
        ),
        "broker_api_called": (
            result.broker_api_called
        ),
        "broker_order_created": (
            result.broker_order_created
        ),
        "live_order_created": (
            result.live_order_created
        ),
        "live_execution_authorized": (
            result.live_execution_authorized
        ),
        "execution_simulated": (
            result.execution_simulated
        ),
        "actual_execution_blocked": (
            result.actual_execution_blocked
        ),
    }

    for field_name, value in boolean_fields.items():
        if not isinstance(
            value,
            bool,
        ):
            raise RuntimeError(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    list_fields = {
        "reasons": result.reasons,
        "warnings": result.warnings,
        "next_actions": result.next_actions,
    }

    for field_name, value in list_fields.items():
        if not isinstance(
            value,
            list,
        ):
            raise RuntimeError(
                f"{field_name}가 List 형식이 아닙니다."
            )

        if not value:
            raise RuntimeError(
                f"{field_name}가 비어 있습니다."
            )

    validate_policy_structure(
        result.paper_broker_policy
    )


def validate_filled_result(
    result: PaperBrokerFillResult,
    request: PaperExecutionRequestResult,
    policy: PaperBrokerPolicy,
) -> None:
    """
    정상 FILLED 결과를 검사합니다.

    Slippage가 0보다 크면:
        BUY 체결가격은 기준가격보다 높아야 합니다.
        SELL 체결가격은 기준가격보다 낮아야 합니다.

    Slippage가 0이면:
        체결가격과 기준가격이 같아야 합니다.
    """

    if result.fill_status != "FILLED":
        raise RuntimeError(
            "정상 결과의 Fill Status가 FILLED가 아닙니다."
        )

    expected_action = (
        "PAPER_BUY_FILL"
        if request.side == "BUY"
        else "PAPER_SELL_FILL"
    )

    if result.fill_action != expected_action:
        raise RuntimeError(
            "Fill Action이 Request Side와 일치하지 않습니다."
        )

    if result.symbol != request.symbol:
        raise RuntimeError(
            "Fill Symbol이 Request Symbol과 일치하지 않습니다."
        )

    if result.request_id != request.request_id:
        raise RuntimeError(
            "Fill Request ID가 원본 Request와 "
            "일치하지 않습니다."
        )

    if result.idempotency_key != request.idempotency_key:
        raise RuntimeError(
            "Fill Idempotency Key가 원본 Request와 "
            "일치하지 않습니다."
        )

    if result.side != request.side:
        raise RuntimeError(
            "Fill Side가 Request Side와 일치하지 않습니다."
        )

    if result.requested_quantity != request.quantity:
        raise RuntimeError(
            "Requested Quantity가 Request와 "
            "일치하지 않습니다."
        )

    if result.filled_quantity != request.quantity:
        raise RuntimeError(
            "Filled Quantity가 Request Quantity와 "
            "일치하지 않습니다."
        )

    if result.unfilled_quantity != 0:
        raise RuntimeError(
            "정상 시장가 체결인데 Unfilled Quantity가 "
            "0이 아닙니다."
        )

    if abs(
        result.reference_price
        - request.reference_price
    ) > 0.0001:
        raise RuntimeError(
            "Reference Price가 Request와 일치하지 않습니다."
        )

    (
        expected_fill_price,
        expected_slippage,
    ) = calculate_fill_price(
        side=request.side,
        reference_price=request.reference_price,
        slippage_percent=policy.slippage_percent,
    )

    if abs(
        result.fill_price
        - expected_fill_price
    ) > 0.0001:
        raise RuntimeError(
            "Fill Price가 예상 계산값과 일치하지 않습니다."
        )

    if abs(
        result.slippage_per_share
        - expected_slippage
    ) > 0.0001:
        raise RuntimeError(
            "Slippage Per Share가 예상값과 "
            "일치하지 않습니다."
        )

    (
        expected_gross_value,
        expected_cash_effect,
    ) = calculate_cash_effect(
        side=request.side,
        quantity=request.quantity,
        fill_price=expected_fill_price,
        commission=policy.commission_per_order,
    )

    if abs(
        result.gross_fill_value
        - expected_gross_value
    ) > 0.01:
        raise RuntimeError(
            "Gross Fill Value가 예상값과 일치하지 않습니다."
        )

    if abs(
        result.total_cash_effect
        - expected_cash_effect
    ) > 0.01:
        raise RuntimeError(
            "Total Cash Effect가 예상값과 일치하지 않습니다."
        )

    if abs(
        result.commission
        - policy.commission_per_order
    ) > 0.01:
        raise RuntimeError(
            "Commission이 Policy와 일치하지 않습니다."
        )

    if request.side == "BUY":
        if policy.slippage_percent > 0:
            if (
                result.fill_price
                <= result.reference_price
            ):
                raise RuntimeError(
                    "BUY 체결가격이 Reference Price보다 "
                    "높지 않습니다."
                )

        else:
            if abs(
                result.fill_price
                - result.reference_price
            ) > 0.0001:
                raise RuntimeError(
                    "Zero Slippage에서는 BUY Fill Price와 "
                    "Reference Price가 같아야 합니다."
                )

        if result.total_cash_effect >= 0:
            raise RuntimeError(
                "BUY Cash Effect가 음수가 아닙니다."
            )

    elif request.side == "SELL":
        if policy.slippage_percent > 0:
            if (
                result.fill_price
                >= result.reference_price
            ):
                raise RuntimeError(
                    "SELL 체결가격이 Reference Price보다 "
                    "낮지 않습니다."
                )

        else:
            if abs(
                result.fill_price
                - result.reference_price
            ) > 0.0001:
                raise RuntimeError(
                    "Zero Slippage에서는 SELL Fill Price와 "
                    "Reference Price가 같아야 합니다."
                )

        if result.total_cash_effect <= 0:
            raise RuntimeError(
                "SELL Cash Effect가 양수가 아닙니다."
            )

    if not result.request_ready:
        raise RuntimeError(
            "Request Ready가 False입니다."
        )

    if not result.request_authorized:
        raise RuntimeError(
            "Request Authorized가 False입니다."
        )

    if not result.request_pending:
        raise RuntimeError(
            "Request Pending이 False입니다."
        )

    if not result.source_loaded:
        raise RuntimeError(
            "Source Loaded가 False입니다."
        )

    if not result.source_valid:
        raise RuntimeError(
            "Source Valid가 False입니다."
        )

    if not result.request_checks_passed:
        raise RuntimeError(
            "Request Checks Passed가 False입니다."
        )

    if not result.policy_checks_passed:
        raise RuntimeError(
            "Policy Checks Passed가 False입니다."
        )

    if not result.duplicate_checks_passed:
        raise RuntimeError(
            "Duplicate Checks Passed가 False입니다."
        )

    if not result.fill_calculation_passed:
        raise RuntimeError(
            "Fill Calculation Passed가 False입니다."
        )

    if not result.fill_generated:
        raise RuntimeError(
            "Fill Generated가 False입니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "All Checks Passed가 False입니다."
        )

    if not result.paper_fill_created:
        raise RuntimeError(
            "Paper Fill Created가 False입니다."
        )

    if not result.execution_simulated:
        raise RuntimeError(
            "Execution Simulated가 False입니다."
        )


def validate_execution_safety(
    result: PaperBrokerFillResult,
) -> None:
    """
    실제 Broker 및 실거래 차단 상태를 검사합니다.
    """

    if result.broker_api_called:
        raise RuntimeError(
            "V9.8에서 실제 Broker API가 호출되었습니다."
        )

    if result.broker_order_created:
        raise RuntimeError(
            "V9.8에서 Broker Order가 생성되었습니다."
        )

    if result.live_order_created:
        raise RuntimeError(
            "V9.8에서 Live Order가 생성되었습니다."
        )

    if result.live_execution_authorized:
        raise RuntimeError(
            "V9.8에서 Live Execution이 허용되었습니다."
        )

    if not result.actual_execution_blocked:
        raise RuntimeError(
            "V9.8에서 실제 Execution이 차단되지 않았습니다."
        )

    warning_text = " ".join(
        str(warning)
        for warning in result.warnings
    ).lower()

    if "broker api" not in warning_text:
        raise RuntimeError(
            "Warnings에 Broker API 미호출 설명이 없습니다."
        )

    if "live execution" not in warning_text:
        raise RuntimeError(
            "Warnings에 Live Execution 차단 설명이 없습니다."
        )

    if "slippage" not in warning_text:
        raise RuntimeError(
            "Warnings에 Slippage 계산 설명이 없습니다."
        )


def validate_fill_id_uniqueness(
    first_result: PaperBrokerFillResult,
    second_result: PaperBrokerFillResult,
) -> None:
    """
    서로 다른 Simulator 실행의 Fill ID가 다른지 검사합니다.
    """

    if first_result.fill_id == second_result.fill_id:
        raise RuntimeError(
            "서로 다른 실행의 Fill ID가 동일합니다."
        )

    if first_result.request_id != second_result.request_id:
        raise RuntimeError(
            "동일 Request를 사용했는데 Request ID가 "
            "변경되었습니다."
        )

    if (
        first_result.idempotency_key
        != second_result.idempotency_key
    ):
        raise RuntimeError(
            "동일 Request를 사용했는데 Idempotency Key가 "
            "변경되었습니다."
        )


def validate_duplicate_scenario(
    symbol: str,
    request: PaperExecutionRequestResult,
    policy: PaperBrokerPolicy,
) -> PaperBrokerFillResult:
    """
    이미 처리된 Idempotency Key를 다시 전달했을 때
    DUPLICATE가 되는지 검사합니다.
    """

    processed_keys = {
        request.idempotency_key,
    }

    result = run_paper_broker_simulator(
        symbol=symbol,
        request=request,
        broker_policy=policy,
        processed_idempotency_keys=processed_keys,
    )

    validate_result_structure(
        result
    )

    if result.fill_status != "DUPLICATE":
        raise RuntimeError(
            "중복 요청의 Fill Status가 DUPLICATE가 아닙니다."
        )

    if result.fill_action != "NO_FILL":
        raise RuntimeError(
            "중복 요청의 Fill Action이 NO_FILL이 아닙니다."
        )

    if result.fill_generated:
        raise RuntimeError(
            "중복 요청에서 Fill이 생성되었습니다."
        )

    if result.paper_fill_created:
        raise RuntimeError(
            "중복 요청에서 Paper Fill이 생성되었습니다."
        )

    if result.execution_simulated:
        raise RuntimeError(
            "중복 요청에서 Execution이 Simulation되었습니다."
        )

    if result.filled_quantity != 0:
        raise RuntimeError(
            "중복 요청의 Filled Quantity가 0이 아닙니다."
        )

    if result.unfilled_quantity != request.quantity:
        raise RuntimeError(
            "중복 요청의 Unfilled Quantity가 "
            "Request Quantity와 일치하지 않습니다."
        )

    if result.duplicate_checks_passed:
        raise RuntimeError(
            "중복 요청에서 Duplicate Checks Passed가 True입니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "중복 요청에서 All Checks Passed가 True입니다."
        )

    validate_execution_safety(
        result
    )

    return result


def validate_duplicate_allowed_scenario(
    symbol: str,
    request: PaperExecutionRequestResult,
) -> PaperBrokerFillResult:
    """
    Duplicate Reject가 False일 때는 동일 요청도
    체결되는지 검사합니다.
    """

    policy = PaperBrokerPolicy(
        reject_duplicate_requests=False,
    )

    processed_keys = {
        request.idempotency_key,
    }

    result = run_paper_broker_simulator(
        symbol=symbol,
        request=request,
        broker_policy=policy,
        processed_idempotency_keys=processed_keys,
    )

    validate_result_structure(
        result
    )

    validate_filled_result(
        result=result,
        request=request,
        policy=policy,
    )

    validate_execution_safety(
        result
    )

    return result


def validate_blocked_policy_scenario(
    symbol: str,
    request: PaperExecutionRequestResult,
) -> PaperBrokerFillResult:
    """
    최대 주문금액이 요청금액보다 작을 때
    BLOCKED가 되는지 검사합니다.
    """

    restrictive_maximum = max(
        0.01,
        request.estimated_order_value
        - 1.0,
    )

    policy = PaperBrokerPolicy(
        maximum_order_value=restrictive_maximum,
    )

    result = run_paper_broker_simulator(
        symbol=symbol,
        request=request,
        broker_policy=policy,
    )

    validate_result_structure(
        result
    )

    if (
        request.estimated_order_value
        > restrictive_maximum
    ):
        if result.fill_status != "BLOCKED":
            raise RuntimeError(
                "제한 Policy 시나리오의 Fill Status가 "
                "BLOCKED가 아닙니다."
            )

        if result.fill_action != "BLOCKED":
            raise RuntimeError(
                "제한 Policy 시나리오의 Fill Action이 "
                "BLOCKED가 아닙니다."
            )

        if result.policy_checks_passed:
            raise RuntimeError(
                "제한 Policy 시나리오에서 "
                "Policy Checks Passed가 True입니다."
            )

        if result.fill_generated:
            raise RuntimeError(
                "제한 Policy 시나리오에서 Fill이 생성되었습니다."
            )

        if result.paper_fill_created:
            raise RuntimeError(
                "제한 Policy 시나리오에서 Paper Fill이 "
                "생성되었습니다."
            )

        if result.all_checks_passed:
            raise RuntimeError(
                "제한 Policy 시나리오에서 "
                "All Checks Passed가 True입니다."
            )

    validate_execution_safety(
        result
    )

    return result


def validate_buy_disabled_scenario(
    symbol: str,
    request: PaperExecutionRequestResult,
) -> PaperBrokerFillResult:
    """
    BUY가 정책에서 금지되었을 때 차단되는지 검사합니다.
    """

    if request.side != "BUY":
        return run_paper_broker_simulator(
            symbol=symbol,
            request=request,
        )

    policy = PaperBrokerPolicy(
        allow_buy=False,
    )

    result = run_paper_broker_simulator(
        symbol=symbol,
        request=request,
        broker_policy=policy,
    )

    if result.fill_status != "BLOCKED":
        raise RuntimeError(
            "BUY Disabled 시나리오가 BLOCKED가 아닙니다."
        )

    if result.paper_fill_created:
        raise RuntimeError(
            "BUY Disabled 시나리오에서 Paper Fill이 "
            "생성되었습니다."
        )

    if result.policy_checks_passed:
        raise RuntimeError(
            "BUY Disabled 시나리오에서 "
            "Policy Checks Passed가 True입니다."
        )

    validate_execution_safety(
        result
    )

    return result


def validate_market_disabled_scenario(
    symbol: str,
    request: PaperExecutionRequestResult,
) -> PaperBrokerFillResult:
    """
    MARKET 주문이 정책에서 금지되었을 때 차단되는지 검사합니다.
    """

    policy = PaperBrokerPolicy(
        allow_market_orders=False,
    )

    result = run_paper_broker_simulator(
        symbol=symbol,
        request=request,
        broker_policy=policy,
    )

    if result.fill_status != "BLOCKED":
        raise RuntimeError(
            "Market Disabled 시나리오가 BLOCKED가 아닙니다."
        )

    if result.paper_fill_created:
        raise RuntimeError(
            "Market Disabled 시나리오에서 Paper Fill이 "
            "생성되었습니다."
        )

    if result.policy_checks_passed:
        raise RuntimeError(
            "Market Disabled 시나리오에서 "
            "Policy Checks Passed가 True입니다."
        )

    validate_execution_safety(
        result
    )

    return result


def validate_commission_scenario(
    symbol: str,
    request: PaperExecutionRequestResult,
) -> PaperBrokerFillResult:
    """
    Commission이 있는 가상 체결을 검사합니다.
    """

    policy = PaperBrokerPolicy(
        commission_per_order=1.0,
        slippage_percent=0.05,
    )

    result = run_paper_broker_simulator(
        symbol=symbol,
        request=request,
        broker_policy=policy,
    )

    validate_result_structure(
        result
    )

    validate_filled_result(
        result=result,
        request=request,
        policy=policy,
    )

    if abs(
        result.commission
        - 1.0
    ) > 0.01:
        raise RuntimeError(
            "Commission 시나리오의 Commission이 "
            "$1.00이 아닙니다."
        )

    if request.side == "BUY":
        expected_cash_effect = -round(
            result.gross_fill_value
            + 1.0,
            2,
        )

    else:
        expected_cash_effect = round(
            result.gross_fill_value
            - 1.0,
            2,
        )

    if abs(
        result.total_cash_effect
        - expected_cash_effect
    ) > 0.01:
        raise RuntimeError(
            "Commission 적용 후 Cash Effect가 "
            "일치하지 않습니다."
        )

    validate_execution_safety(
        result
    )

    return result


def validate_zero_slippage_scenario(
    symbol: str,
    request: PaperExecutionRequestResult,
) -> PaperBrokerFillResult:
    """
    Slippage가 0일 때 Fill Price가 Reference Price와
    같은지 검사합니다.
    """

    policy = PaperBrokerPolicy(
        slippage_percent=0.0,
    )

    result = run_paper_broker_simulator(
        symbol=symbol,
        request=request,
        broker_policy=policy,
    )

    validate_result_structure(
        result
    )

    validate_filled_result(
        result=result,
        request=request,
        policy=policy,
    )

    if abs(
        result.fill_price
        - result.reference_price
    ) > 0.0001:
        raise RuntimeError(
            "Zero Slippage 시나리오에서 Fill Price와 "
            "Reference Price가 일치하지 않습니다."
        )

    if abs(
        result.slippage_per_share
    ) > 0.0001:
        raise RuntimeError(
            "Zero Slippage 시나리오의 "
            "Slippage Per Share가 0이 아닙니다."
        )

    return result


def validate_saved_files(
    result: PaperBrokerFillResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    저장된 V9.8 JSON 파일을 검사합니다.
    """

    if not report_path.exists():
        raise RuntimeError(
            f"Report 파일이 없습니다: {report_path}"
        )

    if not latest_path.exists():
        raise RuntimeError(
            f"Latest 파일이 없습니다: {latest_path}"
        )

    report_payload = load_json_file(
        report_path
    )

    latest_payload = load_json_file(
        latest_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "Report와 Latest JSON 내용이 일치하지 않습니다."
        )

    expected_payload = result.to_dict()

    if report_payload != expected_payload:
        raise RuntimeError(
            "저장된 JSON 내용이 V9.8 실행 결과와 "
            "일치하지 않습니다."
        )

    required_keys = {
        "version",
        "symbol",
        "created_at",
        "fill_id",
        "request_id",
        "idempotency_key",
        "source_request_file",
        "fill_status",
        "fill_status_label",
        "fill_action",
        "fill_action_label",
        "side",
        "requested_quantity",
        "filled_quantity",
        "unfilled_quantity",
        "order_type",
        "time_in_force",
        "reference_price",
        "slippage_percent",
        "slippage_per_share",
        "fill_price",
        "gross_fill_value",
        "commission",
        "total_cash_effect",
        "request_ready",
        "request_authorized",
        "request_pending",
        "source_loaded",
        "source_valid",
        "request_checks_passed",
        "policy_checks_passed",
        "duplicate_checks_passed",
        "fill_calculation_passed",
        "fill_generated",
        "all_checks_passed",
        "paper_fill_created",
        "broker_api_called",
        "broker_order_created",
        "live_order_created",
        "live_execution_authorized",
        "execution_simulated",
        "actual_execution_blocked",
        "paper_broker_policy",
        "reasons",
        "warnings",
        "next_actions",
        "report_path",
        "latest_path",
    }

    missing_keys = (
        required_keys
        - set(report_payload.keys())
    )

    if missing_keys:
        raise RuntimeError(
            "저장된 V9.8 JSON에 필수 키가 없습니다: "
            f"{sorted(missing_keys)}"
        )

    if (
        Path(str(report_payload["report_path"]))
        != report_path
    ):
        raise RuntimeError(
            "JSON 내부 Report Path가 실제 경로와 "
            "일치하지 않습니다."
        )

    if (
        Path(str(report_payload["latest_path"]))
        != latest_path
    ):
        raise RuntimeError(
            "JSON 내부 Latest Path가 실제 경로와 "
            "일치하지 않습니다."
        )


def print_test_result(
    filled_result: PaperBrokerFillResult,
    second_fill_result: PaperBrokerFillResult,
    duplicate_result: PaperBrokerFillResult,
    duplicate_allowed_result: PaperBrokerFillResult,
    blocked_result: PaperBrokerFillResult,
    commission_result: PaperBrokerFillResult,
    zero_slippage_result: PaperBrokerFillResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    V9.8 주요 테스트 결과를 출력합니다.
    """

    print()
    print("=" * 140)
    print(
        "V9.8 PAPER BROKER SIMULATOR TEST RESULT"
    )
    print("=" * 140)

    print("NORMAL PAPER FILL")
    print("-" * 140)

    print(
        f"Fill status                    : "
        f"{filled_result.fill_status}"
    )

    print(
        f"Fill action                    : "
        f"{filled_result.fill_action}"
    )

    print(
        f"Side                           : "
        f"{filled_result.side}"
    )

    print(
        f"Requested quantity             : "
        f"{filled_result.requested_quantity}"
    )

    print(
        f"Filled quantity                : "
        f"{filled_result.filled_quantity}"
    )

    print(
        f"Reference price                : "
        f"${filled_result.reference_price:,.4f}"
    )

    print(
        f"Slippage percent               : "
        f"{filled_result.slippage_percent:.4f}%"
    )

    print(
        f"Slippage per share             : "
        f"${filled_result.slippage_per_share:,.4f}"
    )

    print(
        f"Fill price                     : "
        f"${filled_result.fill_price:,.4f}"
    )

    print(
        f"Gross fill value               : "
        f"${filled_result.gross_fill_value:,.2f}"
    )

    print(
        f"Commission                     : "
        f"${filled_result.commission:,.2f}"
    )

    print(
        f"Total cash effect              : "
        f"${filled_result.total_cash_effect:,.2f}"
    )

    print()
    print("FILL ID AND IDEMPOTENCY")
    print("-" * 140)

    print(
        f"First Fill ID                  : "
        f"{filled_result.fill_id}"
    )

    print(
        f"Second Fill ID                 : "
        f"{second_fill_result.fill_id}"
    )

    print(
        f"Fill IDs differ                : "
        f"{filled_result.fill_id != second_fill_result.fill_id}"
    )

    print(
        f"Request IDs match              : "
        f"{filled_result.request_id == second_fill_result.request_id}"
    )

    print(
        f"Idempotency keys match         : "
        f"{filled_result.idempotency_key == second_fill_result.idempotency_key}"
    )

    print()
    print("DUPLICATE CONTROL")
    print("-" * 140)

    print(
        f"Duplicate rejected status      : "
        f"{duplicate_result.fill_status}"
    )

    print(
        f"Duplicate rejected fill        : "
        f"{duplicate_result.paper_fill_created}"
    )

    print(
        f"Duplicate allowed status       : "
        f"{duplicate_allowed_result.fill_status}"
    )

    print(
        f"Duplicate allowed fill         : "
        f"{duplicate_allowed_result.paper_fill_created}"
    )

    print()
    print("POLICY AND COST SCENARIOS")
    print("-" * 140)

    print(
        f"Blocked policy status          : "
        f"{blocked_result.fill_status}"
    )

    print(
        f"Commission scenario commission : "
        f"${commission_result.commission:,.2f}"
    )

    print(
        f"Commission scenario cash effect: "
        f"${commission_result.total_cash_effect:,.2f}"
    )

    print(
        f"Zero slippage fill price       : "
        f"${zero_slippage_result.fill_price:,.4f}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * 140)

    print(
        f"Paper fill created             : "
        f"{filled_result.paper_fill_created}"
    )

    print(
        f"Execution simulated            : "
        f"{filled_result.execution_simulated}"
    )

    print(
        f"Broker API called              : "
        f"{filled_result.broker_api_called}"
    )

    print(
        f"Broker order created           : "
        f"{filled_result.broker_order_created}"
    )

    print(
        f"Live order created             : "
        f"{filled_result.live_order_created}"
    )

    print(
        f"Live execution authorized      : "
        f"{filled_result.live_execution_authorized}"
    )

    print(
        f"Actual execution blocked       : "
        f"{filled_result.actual_execution_blocked}"
    )

    print()
    print("FILES")
    print("-" * 140)

    print(
        f"Report file                    : "
        f"{report_path}"
    )

    print(
        f"Latest file                    : "
        f"{latest_path}"
    )

    print("=" * 140)


def print_validation_checks(
    filled_result: PaperBrokerFillResult,
    second_fill_result: PaperBrokerFillResult,
    duplicate_result: PaperBrokerFillResult,
    duplicate_allowed_result: PaperBrokerFillResult,
    blocked_result: PaperBrokerFillResult,
    buy_disabled_result: PaperBrokerFillResult,
    market_disabled_result: PaperBrokerFillResult,
    commission_result: PaperBrokerFillResult,
    zero_slippage_result: PaperBrokerFillResult,
    report_path: Path,
    latest_path: Path,
) -> None:
    """
    주요 검증 항목을 True 또는 False로 출력합니다.
    """

    checks = {
        "Version is V9.8": (
            filled_result.version == "V9.8"
        ),
        "Fill status is FILLED": (
            filled_result.fill_status == "FILLED"
        ),
        "Fill action is valid": (
            filled_result.fill_action
            in {
                "PAPER_BUY_FILL",
                "PAPER_SELL_FILL",
            }
        ),
        "Side is valid": (
            filled_result.side in VALID_SIDES
        ),
        "Requested quantity is positive": (
            filled_result.requested_quantity > 0
        ),
        "Filled quantity matches request": (
            filled_result.filled_quantity
            == filled_result.requested_quantity
        ),
        "Unfilled quantity is zero": (
            filled_result.unfilled_quantity == 0
        ),
        "Reference price is positive": (
            filled_result.reference_price > 0
        ),
        "Fill price is positive": (
            filled_result.fill_price > 0
        ),
        "Gross fill value is positive": (
            filled_result.gross_fill_value > 0
        ),
        "Commission is non-negative": (
            filled_result.commission >= 0
        ),
        "Request is ready": (
            filled_result.request_ready
        ),
        "Request is authorized": (
            filled_result.request_authorized
        ),
        "Request is pending": (
            filled_result.request_pending
        ),
        "Source loaded": (
            filled_result.source_loaded
        ),
        "Source valid": (
            filled_result.source_valid
        ),
        "Request checks passed": (
            filled_result.request_checks_passed
        ),
        "Policy checks passed": (
            filled_result.policy_checks_passed
        ),
        "Duplicate checks passed": (
            filled_result.duplicate_checks_passed
        ),
        "Fill calculation passed": (
            filled_result.fill_calculation_passed
        ),
        "Fill generated": (
            filled_result.fill_generated
        ),
        "All checks passed": (
            filled_result.all_checks_passed
        ),
        "Paper fill created": (
            filled_result.paper_fill_created
        ),
        "Execution simulated": (
            filled_result.execution_simulated
        ),
        "Broker API not called": (
            not filled_result.broker_api_called
        ),
        "Broker order not created": (
            not filled_result.broker_order_created
        ),
        "Live order not created": (
            not filled_result.live_order_created
        ),
        "Live execution not authorized": (
            not filled_result.live_execution_authorized
        ),
        "Actual execution remains blocked": (
            filled_result.actual_execution_blocked
        ),
        "Fill ID exists": bool(
            filled_result.fill_id
        ),
        "Request ID exists": bool(
            filled_result.request_id
        ),
        "Idempotency key exists": bool(
            filled_result.idempotency_key
        ),
        "Second Fill ID differs": (
            filled_result.fill_id
            != second_fill_result.fill_id
        ),
        "Second Request ID matches": (
            filled_result.request_id
            == second_fill_result.request_id
        ),
        "Second idempotency key matches": (
            filled_result.idempotency_key
            == second_fill_result.idempotency_key
        ),
        "Duplicate scenario is valid": (
            duplicate_result.fill_status
            == "DUPLICATE"
        ),
        "Duplicate fill not created": (
            not duplicate_result.paper_fill_created
        ),
        "Duplicate allowed scenario filled": (
            duplicate_allowed_result.fill_status
            == "FILLED"
        ),
        "Blocked policy scenario is valid": (
            blocked_result.fill_status
            == "BLOCKED"
        ),
        "Blocked policy fill not created": (
            not blocked_result.paper_fill_created
        ),
        "BUY disabled scenario is safe": (
            (
                buy_disabled_result.fill_status
                == "BLOCKED"
            )
            if filled_result.side == "BUY"
            else True
        ),
        "Market disabled scenario is valid": (
            market_disabled_result.fill_status
            == "BLOCKED"
        ),
        "Commission scenario is filled": (
            commission_result.fill_status
            == "FILLED"
        ),
        "Commission is one dollar": (
            abs(
                commission_result.commission
                - 1.0
            ) <= 0.01
        ),
        "Zero slippage scenario is filled": (
            zero_slippage_result.fill_status
            == "FILLED"
        ),
        "Zero slippage price matches reference": (
            abs(
                zero_slippage_result.fill_price
                - zero_slippage_result.reference_price
            ) <= 0.0001
        ),
        "Policy is immutable": True,
        "Reasons exist": bool(
            filled_result.reasons
        ),
        "Warnings exist": bool(
            filled_result.warnings
        ),
        "Next actions exist": bool(
            filled_result.next_actions
        ),
        "Report file exists": (
            report_path.exists()
        ),
        "Latest file exists": (
            latest_path.exists()
        ),
    }

    print()
    print("=" * 140)
    print("VALIDATION CHECKS")
    print("=" * 140)

    for name, value in checks.items():
        print_check(
            name,
            value,
        )

    print("=" * 140)

    failed_checks = [
        name
        for name, value in checks.items()
        if not value
    ]

    if failed_checks:
        raise RuntimeError(
            "다음 검증 항목이 실패했습니다: "
            f"{failed_checks}"
        )


def main() -> None:
    """
    V9.8 Paper Broker Simulator 통합 테스트입니다.
    """

    symbol = "AAPL"
    account_cash = 10_000.0

    print_header()

    try:
        request = (
            run_paper_execution_request_builder(
                symbol=symbol,
                account_cash=account_cash,
                execution_policy=PaperExecutionPolicy(),
                approval_actor="TEST_USER",
                approval_note=(
                    "V9.8 Paper Broker Simulator "
                    "integration test"
                ),
            )
        )

        (
            request_report_path,
            request_latest_path,
        ) = save_paper_execution_request(
            request
        )

        if not request_report_path.exists():
            raise RuntimeError(
                "V9.7 Request Report 파일이 없습니다."
            )

        if not request_latest_path.exists():
            raise RuntimeError(
                "V9.7 Request Latest 파일이 없습니다."
            )

        validate_request_result(
            request
        )

        broker_policy = PaperBrokerPolicy()

        validate_policy_structure(
            broker_policy
        )

        validate_policy_is_immutable(
            broker_policy
        )

        validate_normal_policy(
            broker_policy
        )

        validate_invalid_policies()

        validate_request_policy(
            request=request,
            policy=broker_policy,
        )

        validate_fill_price_helpers()

        validate_cash_effect_helpers()

        validate_duplicate_helper(
            request
        )

        validate_decision_rules(
            request
        )

        filled_result = run_paper_broker_simulator(
            symbol=symbol,
            request=request,
            broker_policy=broker_policy,
            processed_idempotency_keys=set(),
        )

        validate_result_structure(
            filled_result
        )

        validate_filled_result(
            result=filled_result,
            request=request,
            policy=broker_policy,
        )

        validate_execution_safety(
            filled_result
        )

        second_fill_result = run_paper_broker_simulator(
            symbol=symbol,
            request=request,
            broker_policy=broker_policy,
            processed_idempotency_keys=set(),
        )

        validate_result_structure(
            second_fill_result
        )

        validate_filled_result(
            result=second_fill_result,
            request=request,
            policy=broker_policy,
        )

        validate_fill_id_uniqueness(
            first_result=filled_result,
            second_result=second_fill_result,
        )

        duplicate_result = (
            validate_duplicate_scenario(
                symbol=symbol,
                request=request,
                policy=broker_policy,
            )
        )

        duplicate_allowed_result = (
            validate_duplicate_allowed_scenario(
                symbol=symbol,
                request=request,
            )
        )

        blocked_result = (
            validate_blocked_policy_scenario(
                symbol=symbol,
                request=request,
            )
        )

        buy_disabled_result = (
            validate_buy_disabled_scenario(
                symbol=symbol,
                request=request,
            )
        )

        market_disabled_result = (
            validate_market_disabled_scenario(
                symbol=symbol,
                request=request,
            )
        )

        commission_result = (
            validate_commission_scenario(
                symbol=symbol,
                request=request,
            )
        )

        zero_slippage_result = (
            validate_zero_slippage_scenario(
                symbol=symbol,
                request=request,
            )
        )

        (
            report_path,
            latest_path,
        ) = save_paper_broker_fill(
            filled_result
        )

        validate_saved_files(
            result=filled_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_test_result(
            filled_result=filled_result,
            second_fill_result=second_fill_result,
            duplicate_result=duplicate_result,
            duplicate_allowed_result=duplicate_allowed_result,
            blocked_result=blocked_result,
            commission_result=commission_result,
            zero_slippage_result=zero_slippage_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print_validation_checks(
            filled_result=filled_result,
            second_fill_result=second_fill_result,
            duplicate_result=duplicate_result,
            duplicate_allowed_result=duplicate_allowed_result,
            blocked_result=blocked_result,
            buy_disabled_result=buy_disabled_result,
            market_disabled_result=market_disabled_result,
            commission_result=commission_result,
            zero_slippage_result=zero_slippage_result,
            report_path=report_path,
            latest_path=latest_path,
        )

        print()
        print(
            "V9.8 paper broker simulator "
            "test completed successfully."
        )

        print(
            f"Paper Fill 상태는 "
            f"{filled_result.fill_status}이며 "
            f"Fill Action은 "
            f"{filled_result.fill_action}입니다."
        )

        print(
            f"{filled_result.side} "
            f"{filled_result.filled_quantity}주가 "
            f"${filled_result.fill_price:,.4f}의 "
            f"가상 가격으로 체결되었습니다."
        )

        print(
            f"가상 총 체결금액은 "
            f"${filled_result.gross_fill_value:,.2f}이고 "
            f"현금 변동액은 "
            f"${filled_result.total_cash_effect:,.2f}입니다."
        )

        print(
            "이미 처리된 Idempotency Key는 "
            "DUPLICATE 상태로 정상 차단되었습니다."
        )

        print(
            "Commission, Zero Slippage 및 제한 정책 "
            "시나리오도 정상 검증되었습니다."
        )

        print(
            "실제 Broker API, Broker Order, Live Order 및 "
            "Live Execution은 모두 차단되었습니다."
        )

        print(
            "주의: 이 결과는 연구용 가상 체결이며 "
            "실제 증권 주문이나 실제 시장 체결이 아닙니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 140)
        print("TEST CANCELLED")
        print("=" * 140)

        print(
            "사용자가 V9.8 Paper Broker Simulator "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 140)
        print(
            "V9.8 PAPER BROKER SIMULATOR ERROR"
        )
        print("=" * 140)

        print(
            f"Error type   : "
            f"{type(error).__name__}"
        )

        print(
            f"Error message: "
            f"{error}"
        )

        raise


if __name__ == "__main__":
    main()