import json
import uuid
from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.paper_broker_simulator import (
    PaperBrokerFillResult,
    PaperBrokerPolicy,
    calculate_cash_effect,
    run_paper_broker_simulator,
)
from backtest.paper_portfolio_manager import (
    VALID_PORTFOLIO_ACTIONS,
    VALID_PORTFOLIO_STATUSES,
    VALID_POSITION_STATES,
    PaperPortfolioPolicy,
    PaperPortfolioResult,
    PaperPortfolioState,
    PaperPosition,
    calculate_buy_update,
    calculate_sell_update,
    check_duplicate_fill,
    copy_portfolio_state,
    create_empty_portfolio,
    determine_portfolio_action,
    get_or_create_position,
    load_latest_portfolio_state,
    portfolio_from_dict,
    position_from_dict,
    recalculate_portfolio_totals,
    run_paper_portfolio_manager,
    save_paper_portfolio_result,
    update_position_metrics,
    validate_fill_against_policy,
    validate_paper_fill,
    validate_portfolio_policy,
    validate_portfolio_state,
)


LINE_LENGTH = 140


def print_header() -> None:
    """
    V9.9 테스트 제목을 출력합니다.
    """

    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V9.9 "
        "PAPER PORTFOLIO MANAGER TEST"
    )
    print("=" * LINE_LENGTH)


def print_check(
    name: str,
    value: bool,
) -> None:
    """
    검증 결과를 출력합니다.
    """

    print(
        f"{name:<58}: {value}"
    )


def read_json_file(
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
        payload = json.load(
            file
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise RuntimeError(
            "JSON 최상위 데이터가 Dictionary가 아닙니다."
        )

    return payload


def assert_close(
    actual: float,
    expected: float,
    tolerance: float = 0.01,
    message: str = "숫자 값이 일치하지 않습니다.",
) -> None:
    """
    두 숫자가 허용 오차 이내인지 검사합니다.
    """

    if abs(
        float(actual)
        - float(expected)
    ) > tolerance:
        raise RuntimeError(
            f"{message} "
            f"Actual={actual}, Expected={expected}"
        )


def generate_unique_id() -> str:
    """
    새로운 UUID 문자열을 생성합니다.
    """

    return str(
        uuid.uuid4()
    )


def create_simulated_fill(
    source_fill: PaperBrokerFillResult,
    side: str,
    quantity: int,
    fill_price: float,
    commission: float = 0.0,
    symbol: str = "AAPL",
) -> PaperBrokerFillResult:
    """
    기존 정상 V9.8 결과를 기반으로 테스트용 가상 Fill을 만듭니다.

    실제 Broker 주문은 생성하지 않습니다.
    """

    normalized_side = str(
        side
    ).strip().upper()

    normalized_symbol = str(
        symbol
    ).strip().upper()

    if normalized_side not in {
        "BUY",
        "SELL",
    }:
        raise ValueError(
            "side는 BUY 또는 SELL이어야 합니다."
        )

    if not isinstance(
        quantity,
        int,
    ):
        raise TypeError(
            "quantity는 int 형식이어야 합니다."
        )

    if quantity <= 0:
        raise ValueError(
            "quantity는 0보다 커야 합니다."
        )

    if fill_price <= 0:
        raise ValueError(
            "fill_price는 0보다 커야 합니다."
        )

    if commission < 0:
        raise ValueError(
            "commission은 음수가 될 수 없습니다."
        )

    fill_price = round(
        float(fill_price),
        4,
    )

    gross_fill_value = round(
        quantity
        * fill_price,
        2,
    )

    (
        calculated_gross_value,
        total_cash_effect,
    ) = calculate_cash_effect(
        side=normalized_side,
        quantity=quantity,
        fill_price=fill_price,
        commission=float(commission),
    )

    assert_close(
        actual=calculated_gross_value,
        expected=gross_fill_value,
        message=(
            "테스트 Fill Gross Value 계산이 "
            "일치하지 않습니다."
        ),
    )

    fill_action = (
        "PAPER_BUY_FILL"
        if normalized_side == "BUY"
        else "PAPER_SELL_FILL"
    )

    fill_action_label = (
        "가상 매수 체결"
        if normalized_side == "BUY"
        else "가상 매도 체결"
    )

    now = datetime.now().isoformat()

    return replace(
        source_fill,

        version="V9.8",
        symbol=normalized_symbol,
        created_at=now,

        fill_id=generate_unique_id(),
        request_id=generate_unique_id(),
        idempotency_key=(
            f"{normalized_symbol}_"
            f"{normalized_side}_"
            f"{generate_unique_id()}"
        ),

        source_request_file=None,

        fill_status="FILLED",
        fill_status_label="가상 체결 완료",

        fill_action=fill_action,
        fill_action_label=fill_action_label,

        side=normalized_side,

        requested_quantity=quantity,
        filled_quantity=quantity,
        unfilled_quantity=0,

        order_type="MARKET",
        time_in_force="DAY",

        reference_price=fill_price,
        slippage_percent=0.0,
        slippage_per_share=0.0,
        fill_price=fill_price,

        gross_fill_value=gross_fill_value,
        commission=round(
            float(commission),
            2,
        ),
        total_cash_effect=round(
            total_cash_effect,
            2,
        ),

        request_ready=True,
        request_authorized=True,
        request_pending=True,

        source_loaded=True,
        source_valid=True,

        request_checks_passed=True,
        policy_checks_passed=True,
        duplicate_checks_passed=True,
        fill_calculation_passed=True,

        fill_generated=True,
        all_checks_passed=True,

        paper_fill_created=True,

        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,

        execution_simulated=True,
        actual_execution_blocked=True,

        paper_broker_policy=PaperBrokerPolicy(
            commission_per_order=float(
                commission
            ),
            slippage_percent=0.0,
        ),

        reasons=[
            (
                "V9.9 Paper Portfolio Manager "
                "테스트용 가상 체결입니다."
            ),
            (
                f"{normalized_side} "
                f"{quantity}주 체결 결과입니다."
            ),
        ],

        warnings=[
            (
                "실제 Broker API는 호출되지 않았습니다."
            ),
            (
                "Live Execution은 차단되었습니다."
            ),
            (
                "테스트용 Slippage는 0%입니다."
            ),
        ],

        next_actions=[
            (
                "V9.9 Paper Portfolio Manager로 "
                "가상 체결을 전달합니다."
            ),
        ],

        report_path=None,
        latest_path=None,
    )


def create_normal_source_fill(
    symbol: str,
    initial_cash: float,
) -> PaperBrokerFillResult:
    """
    V9.8 Simulator를 실행해 정상 Source Fill을 생성합니다.
    """

    result = run_paper_broker_simulator(
        symbol=symbol,
        account_cash=initial_cash,
    )

    (
        valid,
        errors,
    ) = validate_paper_fill(
        result
    )

    if not valid:
        raise RuntimeError(
            "V9.8 Source Fill이 유효하지 않습니다: "
            f"{errors}"
        )

    return result


def validate_policy_structure(
    policy: PaperPortfolioPolicy,
) -> None:
    """
    PaperPortfolioPolicy의 기본 구조를 검사합니다.
    """

    if not isinstance(
        policy,
        PaperPortfolioPolicy,
    ):
        raise RuntimeError(
            "Policy가 PaperPortfolioPolicy 형식이 아닙니다."
        )

    expected_keys = {
        "minimum_cash_balance",
        "maximum_position_shares",
        "maximum_position_value",
        "allow_buy",
        "allow_sell",
        "allow_add_to_position",
        "allow_partial_exit",
        "allow_short_selling",
        "prevent_negative_cash",
        "prevent_negative_shares",
        "reject_duplicate_fills",
        "paper_only",
        "live_execution_disabled",
    }

    actual_keys = set(
        policy.to_dict().keys()
    )

    if actual_keys != expected_keys:
        raise RuntimeError(
            "PaperPortfolioPolicy.to_dict() 구조가 "
            "예상 결과와 일치하지 않습니다."
        )

    (
        valid,
        errors,
    ) = validate_portfolio_policy(
        policy
    )

    if not valid:
        raise RuntimeError(
            "기본 Portfolio Policy가 유효하지 않습니다: "
            f"{errors}"
        )

    if errors:
        raise RuntimeError(
            "정상 Portfolio Policy 검사에서 "
            "오류 메시지가 생성되었습니다."
        )


def validate_policy_is_immutable(
    policy: PaperPortfolioPolicy,
) -> None:
    """
    PaperPortfolioPolicy가 Frozen Dataclass인지 검사합니다.
    """

    original_value = (
        policy.maximum_position_shares
    )

    immutable = False

    try:
        policy.maximum_position_shares = 1

    except (
        FrozenInstanceError,
        AttributeError,
    ):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "PaperPortfolioPolicy 값을 직접 변경할 수 있습니다."
        )

    if (
        policy.maximum_position_shares
        != original_value
    ):
        raise RuntimeError(
            "불변 Policy의 값이 변경되었습니다."
        )


def validate_invalid_policies() -> None:
    """
    잘못된 Portfolio Policy들이 거부되는지 검사합니다.
    """

    invalid_policies = [
        PaperPortfolioPolicy(
            minimum_cash_balance=-1.0,
        ),
        PaperPortfolioPolicy(
            maximum_position_shares=0,
        ),
        PaperPortfolioPolicy(
            maximum_position_shares=-1,
        ),
        PaperPortfolioPolicy(
            maximum_position_value=0.0,
        ),
        PaperPortfolioPolicy(
            maximum_position_value=-1.0,
        ),
        PaperPortfolioPolicy(
            allow_short_selling=True,
        ),
        PaperPortfolioPolicy(
            paper_only=False,
        ),
        PaperPortfolioPolicy(
            live_execution_disabled=False,
        ),
    ]

    for policy in invalid_policies:
        (
            valid,
            errors,
        ) = validate_portfolio_policy(
            policy
        )

        if valid:
            raise RuntimeError(
                "잘못된 Portfolio Policy가 "
                "유효한 것으로 판정되었습니다."
            )

        if not errors:
            raise RuntimeError(
                "잘못된 Policy 검사에서 오류 메시지가 "
                "생성되지 않았습니다."
            )


def validate_empty_portfolio(
    portfolio: PaperPortfolioState,
    expected_cash: float,
) -> None:
    """
    신규 빈 Portfolio를 검사합니다.
    """

    if not isinstance(
        portfolio,
        PaperPortfolioState,
    ):
        raise RuntimeError(
            "Portfolio가 PaperPortfolioState 형식이 아닙니다."
        )

    if not portfolio.portfolio_id:
        raise RuntimeError(
            "Portfolio ID가 비어 있습니다."
        )

    assert_close(
        actual=portfolio.initial_cash,
        expected=expected_cash,
        message="Initial Cash가 일치하지 않습니다.",
    )

    assert_close(
        actual=portfolio.cash_balance,
        expected=expected_cash,
        message="초기 Cash Balance가 일치하지 않습니다.",
    )

    assert_close(
        actual=portfolio.total_market_value,
        expected=0.0,
        message="초기 Market Value가 0이 아닙니다.",
    )

    assert_close(
        actual=portfolio.total_equity,
        expected=expected_cash,
        message="초기 Total Equity가 일치하지 않습니다.",
    )

    if portfolio.positions:
        raise RuntimeError(
            "신규 Portfolio에 Position이 존재합니다."
        )

    if portfolio.processed_fill_ids:
        raise RuntimeError(
            "신규 Portfolio에 처리된 Fill ID가 존재합니다."
        )

    if portfolio.processed_idempotency_keys:
        raise RuntimeError(
            "신규 Portfolio에 처리된 Idempotency Key가 "
            "존재합니다."
        )

    (
        valid,
        errors,
    ) = validate_portfolio_state(
        portfolio
    )

    if not valid:
        raise RuntimeError(
            "신규 Portfolio 상태가 유효하지 않습니다: "
            f"{errors}"
        )


def validate_position_helpers(
    symbol: str,
) -> None:
    """
    Position 생성, 복사 및 Dictionary 변환을 검사합니다.
    """

    portfolio = create_empty_portfolio(
        initial_cash=10_000.0
    )

    position = get_or_create_position(
        portfolio=portfolio,
        symbol=symbol,
    )

    if not isinstance(
        position,
        PaperPosition,
    ):
        raise RuntimeError(
            "Position이 PaperPosition 형식이 아닙니다."
        )

    if position.symbol != symbol:
        raise RuntimeError(
            "Position Symbol이 일치하지 않습니다."
        )

    if position.state != "FLAT":
        raise RuntimeError(
            "신규 Position State가 FLAT이 아닙니다."
        )

    if position.shares != 0:
        raise RuntimeError(
            "신규 Position Shares가 0이 아닙니다."
        )

    converted_position = position_from_dict(
        position.to_dict()
    )

    if converted_position.to_dict() != position.to_dict():
        raise RuntimeError(
            "Position Dictionary 변환 결과가 "
            "원본과 일치하지 않습니다."
        )

    copied_portfolio = copy_portfolio_state(
        portfolio
    )

    if (
        copied_portfolio.to_dict()
        != portfolio.to_dict()
    ):
        raise RuntimeError(
            "Portfolio 복사 결과가 원본과 일치하지 않습니다."
        )

    copied_portfolio.cash_balance = 1.0

    if (
        copied_portfolio.cash_balance
        == portfolio.cash_balance
    ):
        raise RuntimeError(
            "Portfolio가 독립적으로 복사되지 않았습니다."
        )


def validate_action_rules() -> None:
    """
    Portfolio Action 결정 규칙을 검사합니다.
    """

    open_action = determine_portfolio_action(
        side="BUY",
        previous_shares=0,
        fill_quantity=4,
    )

    if open_action[0] != "OPEN_LONG":
        raise RuntimeError(
            "신규 BUY Action이 OPEN_LONG이 아닙니다."
        )

    add_action = determine_portfolio_action(
        side="BUY",
        previous_shares=4,
        fill_quantity=2,
    )

    if add_action[0] != "ADD_LONG":
        raise RuntimeError(
            "추가 BUY Action이 ADD_LONG이 아닙니다."
        )

    reduce_action = determine_portfolio_action(
        side="SELL",
        previous_shares=6,
        fill_quantity=2,
    )

    if reduce_action[0] != "REDUCE_LONG":
        raise RuntimeError(
            "부분 SELL Action이 REDUCE_LONG이 아닙니다."
        )

    close_action = determine_portfolio_action(
        side="SELL",
        previous_shares=4,
        fill_quantity=4,
    )

    if close_action[0] != "CLOSE_LONG":
        raise RuntimeError(
            "전체 SELL Action이 CLOSE_LONG이 아닙니다."
        )

    blocked_action = determine_portfolio_action(
        side="SELL",
        previous_shares=4,
        fill_quantity=5,
    )

    if blocked_action[0] != "BLOCKED":
        raise RuntimeError(
            "초과 SELL Action이 BLOCKED가 아닙니다."
        )


def validate_calculation_helpers(
    source_fill: PaperBrokerFillResult,
) -> None:
    """
    BUY 및 SELL Portfolio 계산 Helper를 검사합니다.
    """

    position = PaperPosition(
        symbol="AAPL",
        state="FLAT",
        shares=0,
        average_price=0.0,
        cost_basis=0.0,
    )

    buy_fill = create_simulated_fill(
        source_fill=source_fill,
        side="BUY",
        quantity=4,
        fill_price=100.0,
        commission=1.0,
    )

    (
        updated_shares,
        updated_average_price,
        updated_cost_basis,
    ) = calculate_buy_update(
        position=position,
        fill=buy_fill,
    )

    if updated_shares != 4:
        raise RuntimeError(
            "BUY Helper의 Updated Shares가 4가 아닙니다."
        )

    assert_close(
        actual=updated_cost_basis,
        expected=401.0,
        message="BUY Helper Cost Basis가 일치하지 않습니다.",
    )

    assert_close(
        actual=updated_average_price,
        expected=100.25,
        tolerance=0.0001,
        message="BUY Helper Average Price가 일치하지 않습니다.",
    )

    position.state = "LONG"
    position.shares = updated_shares
    position.average_price = updated_average_price
    position.cost_basis = updated_cost_basis

    sell_fill = create_simulated_fill(
        source_fill=source_fill,
        side="SELL",
        quantity=2,
        fill_price=110.0,
        commission=1.0,
    )

    (
        remaining_shares,
        remaining_average_price,
        remaining_cost_basis,
        transaction_realized_pnl,
    ) = calculate_sell_update(
        position=position,
        fill=sell_fill,
    )

    if remaining_shares != 2:
        raise RuntimeError(
            "SELL Helper의 Remaining Shares가 2가 아닙니다."
        )

    assert_close(
        actual=remaining_cost_basis,
        expected=200.50,
        message=(
            "SELL Helper의 Remaining Cost Basis가 "
            "일치하지 않습니다."
        ),
    )

    assert_close(
        actual=remaining_average_price,
        expected=100.25,
        tolerance=0.0001,
        message=(
            "부분 매도 후 Average Price가 "
            "유지되지 않았습니다."
        ),
    )

    assert_close(
        actual=transaction_realized_pnl,
        expected=18.50,
        message=(
            "SELL Helper의 Realized PnL이 "
            "일치하지 않습니다."
        ),
    )


def validate_result_common(
    result: PaperPortfolioResult,
) -> None:
    """
    모든 V9.9 결과에 공통으로 필요한 구조를 검사합니다.
    """

    if not isinstance(
        result,
        PaperPortfolioResult,
    ):
        raise RuntimeError(
            "결과가 PaperPortfolioResult 형식이 아닙니다."
        )

    if result.version != "V9.9":
        raise RuntimeError(
            f"Version이 V9.9가 아닙니다: {result.version}"
        )

    if not result.symbol:
        raise RuntimeError(
            "Result Symbol이 비어 있습니다."
        )

    if result.symbol != result.symbol.upper():
        raise RuntimeError(
            "Result Symbol이 대문자로 정규화되지 않았습니다."
        )

    if not result.update_id:
        raise RuntimeError(
            "Update ID가 비어 있습니다."
        )

    if not result.source_fill_id:
        raise RuntimeError(
            "Source Fill ID가 비어 있습니다."
        )

    if not result.source_request_id:
        raise RuntimeError(
            "Source Request ID가 비어 있습니다."
        )

    if not result.source_idempotency_key:
        raise RuntimeError(
            "Source Idempotency Key가 비어 있습니다."
        )

    if (
        result.portfolio_status
        not in VALID_PORTFOLIO_STATUSES
    ):
        raise RuntimeError(
            "Portfolio Status가 유효하지 않습니다: "
            f"{result.portfolio_status}"
        )

    if (
        result.portfolio_action
        not in VALID_PORTFOLIO_ACTIONS
    ):
        raise RuntimeError(
            "Portfolio Action이 유효하지 않습니다: "
            f"{result.portfolio_action}"
        )

    if (
        result.previous_position_state
        not in VALID_POSITION_STATES
    ):
        raise RuntimeError(
            "Previous Position State가 유효하지 않습니다."
        )

    if (
        result.updated_position_state
        not in VALID_POSITION_STATES
    ):
        raise RuntimeError(
            "Updated Position State가 유효하지 않습니다."
        )

    if not isinstance(
        result.fill_quantity,
        int,
    ):
        raise RuntimeError(
            "Fill Quantity가 int 형식이 아닙니다."
        )

    if not isinstance(
        result.previous_shares,
        int,
    ):
        raise RuntimeError(
            "Previous Shares가 int 형식이 아닙니다."
        )

    if not isinstance(
        result.updated_shares,
        int,
    ):
        raise RuntimeError(
            "Updated Shares가 int 형식이 아닙니다."
        )

    if not isinstance(
        result.share_change,
        int,
    ):
        raise RuntimeError(
            "Share Change가 int 형식이 아닙니다."
        )

    if (
        result.updated_shares
        - result.previous_shares
        != result.share_change
    ):
        raise RuntimeError(
            "Share Change 계산이 일치하지 않습니다."
        )

    numeric_fields = {
        "fill_price": result.fill_price,
        "fill_value": result.fill_value,
        "commission": result.commission,
        "cash_effect": result.cash_effect,
        "previous_cash_balance": (
            result.previous_cash_balance
        ),
        "updated_cash_balance": (
            result.updated_cash_balance
        ),
        "cash_change": result.cash_change,
        "previous_average_price": (
            result.previous_average_price
        ),
        "updated_average_price": (
            result.updated_average_price
        ),
        "previous_cost_basis": (
            result.previous_cost_basis
        ),
        "updated_cost_basis": (
            result.updated_cost_basis
        ),
        "latest_price": result.latest_price,
        "position_market_value": (
            result.position_market_value
        ),
        "transaction_realized_pnl": (
            result.transaction_realized_pnl
        ),
        "position_realized_pnl": (
            result.position_realized_pnl
        ),
        "position_unrealized_pnl": (
            result.position_unrealized_pnl
        ),
        "position_unrealized_pnl_percent": (
            result.position_unrealized_pnl_percent
        ),
        "total_market_value": (
            result.total_market_value
        ),
        "total_unrealized_pnl": (
            result.total_unrealized_pnl
        ),
        "total_realized_pnl": (
            result.total_realized_pnl
        ),
        "total_equity": result.total_equity,
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
        "source_loaded": result.source_loaded,
        "source_valid": result.source_valid,
        "portfolio_loaded": result.portfolio_loaded,
        "portfolio_valid": result.portfolio_valid,
        "policy_checks_passed": (
            result.policy_checks_passed
        ),
        "duplicate_checks_passed": (
            result.duplicate_checks_passed
        ),
        "cash_checks_passed": (
            result.cash_checks_passed
        ),
        "position_checks_passed": (
            result.position_checks_passed
        ),
        "calculation_checks_passed": (
            result.calculation_checks_passed
        ),
        "portfolio_updated": (
            result.portfolio_updated
        ),
        "all_checks_passed": (
            result.all_checks_passed
        ),
        "duplicate_fill": result.duplicate_fill,
        "execution_blocked": (
            result.execution_blocked
        ),
        "broker_api_called": (
            result.broker_api_called
        ),
        "live_order_created": (
            result.live_order_created
        ),
        "live_execution_authorized": (
            result.live_execution_authorized
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

    if not isinstance(
        result.portfolio_policy,
        PaperPortfolioPolicy,
    ):
        raise RuntimeError(
            "Result Portfolio Policy 형식이 올바르지 않습니다."
        )

    if not isinstance(
        result.portfolio_state,
        PaperPortfolioState,
    ):
        raise RuntimeError(
            "Result Portfolio State 형식이 올바르지 않습니다."
        )

    if not result.reasons:
        raise RuntimeError(
            "Reasons가 비어 있습니다."
        )

    if not result.warnings:
        raise RuntimeError(
            "Warnings가 비어 있습니다."
        )

    if not result.next_actions:
        raise RuntimeError(
            "Next Actions가 비어 있습니다."
        )

    if not result.execution_blocked:
        raise RuntimeError(
            "실제 Execution이 차단되지 않았습니다."
        )

    if result.broker_api_called:
        raise RuntimeError(
            "실제 Broker API가 호출되었습니다."
        )

    if result.live_order_created:
        raise RuntimeError(
            "Live Order가 생성되었습니다."
        )

    if result.live_execution_authorized:
        raise RuntimeError(
            "Live Execution이 허용되었습니다."
        )

    expected_equity = round(
        result.updated_cash_balance
        + result.total_market_value,
        2,
    )

    assert_close(
        actual=result.total_equity,
        expected=expected_equity,
        message=(
            "Result Total Equity가 Cash + Market Value와 "
            "일치하지 않습니다."
        ),
    )

    (
        portfolio_valid,
        portfolio_errors,
    ) = validate_portfolio_state(
        result.portfolio_state
    )

    if not portfolio_valid:
        raise RuntimeError(
            "Result 내부 Portfolio 상태가 유효하지 않습니다: "
            f"{portfolio_errors}"
        )


def validate_success_result(
    result: PaperPortfolioResult,
    expected_action: str,
    expected_previous_shares: int,
    expected_updated_shares: int,
) -> None:
    """
    정상 Portfolio 업데이트 결과를 검사합니다.
    """

    validate_result_common(
        result
    )

    if result.portfolio_status != "UPDATED":
        raise RuntimeError(
            "정상 결과의 Portfolio Status가 UPDATED가 아닙니다."
        )

    if result.portfolio_action != expected_action:
        raise RuntimeError(
            f"Portfolio Action이 {expected_action}이 아닙니다."
        )

    if result.previous_shares != expected_previous_shares:
        raise RuntimeError(
            "Previous Shares가 예상값과 일치하지 않습니다."
        )

    if result.updated_shares != expected_updated_shares:
        raise RuntimeError(
            "Updated Shares가 예상값과 일치하지 않습니다."
        )

    if not result.source_loaded:
        raise RuntimeError(
            "Source Loaded가 False입니다."
        )

    if not result.source_valid:
        raise RuntimeError(
            "Source Valid가 False입니다."
        )

    if not result.portfolio_loaded:
        raise RuntimeError(
            "Portfolio Loaded가 False입니다."
        )

    if not result.portfolio_valid:
        raise RuntimeError(
            "Portfolio Valid가 False입니다."
        )

    if not result.policy_checks_passed:
        raise RuntimeError(
            "Policy Checks Passed가 False입니다."
        )

    if not result.duplicate_checks_passed:
        raise RuntimeError(
            "Duplicate Checks Passed가 False입니다."
        )

    if not result.cash_checks_passed:
        raise RuntimeError(
            "Cash Checks Passed가 False입니다."
        )

    if not result.position_checks_passed:
        raise RuntimeError(
            "Position Checks Passed가 False입니다."
        )

    if not result.calculation_checks_passed:
        raise RuntimeError(
            "Calculation Checks Passed가 False입니다."
        )

    if not result.portfolio_updated:
        raise RuntimeError(
            "Portfolio Updated가 False입니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "All Checks Passed가 False입니다."
        )

    if result.duplicate_fill:
        raise RuntimeError(
            "정상 결과가 Duplicate Fill로 판정되었습니다."
        )


def validate_open_long_scenario(
    symbol: str,
    initial_cash: float,
    fill: PaperBrokerFillResult,
) -> PaperPortfolioResult:
    """
    신규 매수 OPEN_LONG 시나리오를 검사합니다.
    """

    portfolio = create_empty_portfolio(
        initial_cash=initial_cash
    )

    result = run_paper_portfolio_manager(
        symbol=symbol,
        fill_result=fill,
        portfolio_state=portfolio,
        portfolio_policy=PaperPortfolioPolicy(),
        initial_cash=initial_cash,
    )

    validate_success_result(
        result=result,
        expected_action="OPEN_LONG",
        expected_previous_shares=0,
        expected_updated_shares=fill.filled_quantity,
    )

    expected_cash = round(
        initial_cash
        + fill.total_cash_effect,
        2,
    )

    expected_cost_basis = round(
        fill.gross_fill_value
        + fill.commission,
        2,
    )

    assert_close(
        actual=result.updated_cash_balance,
        expected=expected_cash,
        message="OPEN_LONG Cash Balance가 일치하지 않습니다.",
    )

    assert_close(
        actual=result.updated_cost_basis,
        expected=expected_cost_basis,
        message="OPEN_LONG Cost Basis가 일치하지 않습니다.",
    )

    assert_close(
        actual=result.updated_average_price,
        expected=(
            expected_cost_basis
            / fill.filled_quantity
        ),
        tolerance=0.0001,
        message="OPEN_LONG Average Price가 일치하지 않습니다.",
    )

    if result.updated_position_state != "LONG":
        raise RuntimeError(
            "OPEN_LONG 이후 Position State가 LONG이 아닙니다."
        )

    if (
        fill.fill_id
        not in result.portfolio_state.processed_fill_ids
    ):
        raise RuntimeError(
            "처리된 Fill ID가 Portfolio에 저장되지 않았습니다."
        )

    if (
        fill.idempotency_key
        not in result.portfolio_state.processed_idempotency_keys
    ):
        raise RuntimeError(
            "처리된 Idempotency Key가 Portfolio에 "
            "저장되지 않았습니다."
        )

    return result


def validate_duplicate_scenario(
    symbol: str,
    original_result: PaperPortfolioResult,
    original_fill: PaperBrokerFillResult,
) -> PaperPortfolioResult:
    """
    동일 Fill을 다시 반영할 때 NO_CHANGE가 되는지 검사합니다.
    """

    portfolio_before = original_result.portfolio_state.to_dict()

    duplicate_result = run_paper_portfolio_manager(
        symbol=symbol,
        fill_result=original_fill,
        portfolio_state=original_result.portfolio_state,
        portfolio_policy=PaperPortfolioPolicy(
            reject_duplicate_fills=True,
        ),
    )

    validate_result_common(
        duplicate_result
    )

    if duplicate_result.portfolio_status != "NO_CHANGE":
        raise RuntimeError(
            "중복 Fill Status가 NO_CHANGE가 아닙니다."
        )

    if duplicate_result.portfolio_action != "NO_ACTION":
        raise RuntimeError(
            "중복 Fill Action이 NO_ACTION이 아닙니다."
        )

    if not duplicate_result.duplicate_fill:
        raise RuntimeError(
            "중복 Fill이 감지되지 않았습니다."
        )

    if duplicate_result.duplicate_checks_passed:
        raise RuntimeError(
            "중복 Fill에서 Duplicate Checks Passed가 "
            "True입니다."
        )

    if duplicate_result.portfolio_updated:
        raise RuntimeError(
            "중복 Fill에서 Portfolio가 변경되었습니다."
        )

    if duplicate_result.all_checks_passed:
        raise RuntimeError(
            "중복 Fill에서 All Checks Passed가 True입니다."
        )

    portfolio_after = (
        duplicate_result.portfolio_state.to_dict()
    )

    if portfolio_before != portfolio_after:
        raise RuntimeError(
            "중복 Fill 차단 후 Portfolio 상태가 변경되었습니다."
        )

    return duplicate_result


def validate_add_long_scenario(
    symbol: str,
    previous_result: PaperPortfolioResult,
    fill: PaperBrokerFillResult,
) -> PaperPortfolioResult:
    """
    추가 매수 ADD_LONG 시나리오를 검사합니다.
    """

    previous_position = (
        previous_result.portfolio_state.positions[
            symbol
        ]
    )

    previous_shares = previous_position.shares
    previous_cost_basis = previous_position.cost_basis

    result = run_paper_portfolio_manager(
        symbol=symbol,
        fill_result=fill,
        portfolio_state=previous_result.portfolio_state,
        portfolio_policy=PaperPortfolioPolicy(),
    )

    expected_shares = (
        previous_shares
        + fill.filled_quantity
    )

    validate_success_result(
        result=result,
        expected_action="ADD_LONG",
        expected_previous_shares=previous_shares,
        expected_updated_shares=expected_shares,
    )

    expected_cost_basis = round(
        previous_cost_basis
        + fill.gross_fill_value
        + fill.commission,
        2,
    )

    expected_average_price = round(
        expected_cost_basis
        / expected_shares,
        4,
    )

    assert_close(
        actual=result.updated_cost_basis,
        expected=expected_cost_basis,
        message="ADD_LONG Cost Basis가 일치하지 않습니다.",
    )

    assert_close(
        actual=result.updated_average_price,
        expected=expected_average_price,
        tolerance=0.0001,
        message="ADD_LONG Average Price가 일치하지 않습니다.",
    )

    return result


def validate_partial_sell_scenario(
    symbol: str,
    previous_result: PaperPortfolioResult,
    sell_fill: PaperBrokerFillResult,
) -> PaperPortfolioResult:
    """
    부분 매도 REDUCE_LONG 시나리오를 검사합니다.
    """

    previous_position = (
        previous_result.portfolio_state.positions[
            symbol
        ]
    )

    previous_shares = previous_position.shares
    previous_average_price = (
        previous_position.average_price
    )

    result = run_paper_portfolio_manager(
        symbol=symbol,
        fill_result=sell_fill,
        portfolio_state=previous_result.portfolio_state,
        portfolio_policy=PaperPortfolioPolicy(),
    )

    expected_shares = (
        previous_shares
        - sell_fill.filled_quantity
    )

    validate_success_result(
        result=result,
        expected_action="REDUCE_LONG",
        expected_previous_shares=previous_shares,
        expected_updated_shares=expected_shares,
    )

    if result.updated_position_state != "LONG":
        raise RuntimeError(
            "부분 매도 후 Position State가 LONG이 아닙니다."
        )

    assert_close(
        actual=result.updated_average_price,
        expected=previous_average_price,
        tolerance=0.001,
        message=(
            "부분 매도 후 Average Price가 "
            "유지되지 않았습니다."
        ),
    )

    expected_cost_removed = round(
        previous_average_price
        * sell_fill.filled_quantity,
        2,
    )

    expected_net_proceeds = round(
        sell_fill.gross_fill_value
        - sell_fill.commission,
        2,
    )

    expected_realized_pnl = round(
        expected_net_proceeds
        - expected_cost_removed,
        2,
    )

    assert_close(
        actual=result.transaction_realized_pnl,
        expected=expected_realized_pnl,
        message=(
            "부분 매도 Transaction Realized PnL이 "
            "일치하지 않습니다."
        ),
    )

    return result


def validate_close_long_scenario(
    symbol: str,
    previous_result: PaperPortfolioResult,
    sell_fill: PaperBrokerFillResult,
) -> PaperPortfolioResult:
    """
    전체 매도 CLOSE_LONG 시나리오를 검사합니다.
    """

    previous_shares = (
        previous_result.portfolio_state.positions[
            symbol
        ].shares
    )

    if sell_fill.filled_quantity != previous_shares:
        raise RuntimeError(
            "CLOSE_LONG 테스트 매도 수량이 "
            "보유 수량과 일치하지 않습니다."
        )

    result = run_paper_portfolio_manager(
        symbol=symbol,
        fill_result=sell_fill,
        portfolio_state=previous_result.portfolio_state,
        portfolio_policy=PaperPortfolioPolicy(),
    )

    validate_success_result(
        result=result,
        expected_action="CLOSE_LONG",
        expected_previous_shares=previous_shares,
        expected_updated_shares=0,
    )

    if result.updated_position_state != "FLAT":
        raise RuntimeError(
            "전체 매도 후 Position State가 FLAT이 아닙니다."
        )

    assert_close(
        actual=result.updated_average_price,
        expected=0.0,
        tolerance=0.0001,
        message=(
            "전체 매도 후 Average Price가 0이 아닙니다."
        ),
    )

    assert_close(
        actual=result.updated_cost_basis,
        expected=0.0,
        message=(
            "전체 매도 후 Cost Basis가 0이 아닙니다."
        ),
    )

    assert_close(
        actual=result.position_market_value,
        expected=0.0,
        message=(
            "전체 매도 후 Position Market Value가 "
            "0이 아닙니다."
        ),
    )

    assert_close(
        actual=result.position_unrealized_pnl,
        expected=0.0,
        message=(
            "전체 매도 후 Unrealized PnL이 0이 아닙니다."
        ),
    )

    return result


def validate_oversell_scenario(
    symbol: str,
    source_portfolio: PaperPortfolioState,
    source_fill: PaperBrokerFillResult,
) -> PaperPortfolioResult:
    """
    보유 수량 초과 매도가 차단되는지 검사합니다.
    """

    position = source_portfolio.positions[
        symbol
    ]

    oversell_quantity = (
        position.shares
        + 1
    )

    oversell_fill = create_simulated_fill(
        source_fill=source_fill,
        side="SELL",
        quantity=oversell_quantity,
        fill_price=max(
            position.latest_price,
            1.0,
        ),
    )

    portfolio_before = (
        source_portfolio.to_dict()
    )

    result = run_paper_portfolio_manager(
        symbol=symbol,
        fill_result=oversell_fill,
        portfolio_state=source_portfolio,
        portfolio_policy=PaperPortfolioPolicy(
            prevent_negative_shares=True,
            allow_short_selling=False,
        ),
    )

    validate_result_common(
        result
    )

    if result.portfolio_status != "BLOCKED":
        raise RuntimeError(
            "초과 매도 Status가 BLOCKED가 아닙니다."
        )

    if result.portfolio_action != "BLOCKED":
        raise RuntimeError(
            "초과 매도 Action이 BLOCKED가 아닙니다."
        )

    if result.policy_checks_passed:
        raise RuntimeError(
            "초과 매도에서 Policy Checks Passed가 True입니다."
        )

    if result.portfolio_updated:
        raise RuntimeError(
            "초과 매도에서 Portfolio가 변경되었습니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "초과 매도에서 All Checks Passed가 True입니다."
        )

    if (
        portfolio_before
        != result.portfolio_state.to_dict()
    ):
        raise RuntimeError(
            "초과 매도 차단 후 Portfolio 상태가 변경되었습니다."
        )

    return result


def validate_insufficient_cash_scenario(
    symbol: str,
    source_fill: PaperBrokerFillResult,
) -> PaperPortfolioResult:
    """
    현금이 부족한 BUY Fill이 차단되는지 검사합니다.
    """

    small_portfolio = create_empty_portfolio(
        initial_cash=1_000.0
    )

    expensive_fill = create_simulated_fill(
        source_fill=source_fill,
        side="BUY",
        quantity=10,
        fill_price=500.0,
        commission=0.0,
    )

    result = run_paper_portfolio_manager(
        symbol=symbol,
        fill_result=expensive_fill,
        portfolio_state=small_portfolio,
        portfolio_policy=PaperPortfolioPolicy(
            prevent_negative_cash=True,
            minimum_cash_balance=0.0,
            maximum_position_value=1_000_000.0,
        ),
        initial_cash=1_000.0,
    )

    validate_result_common(
        result
    )

    if result.portfolio_status != "BLOCKED":
        raise RuntimeError(
            "현금 부족 시나리오 Status가 BLOCKED가 아닙니다."
        )

    if result.portfolio_action != "BLOCKED":
        raise RuntimeError(
            "현금 부족 시나리오 Action이 BLOCKED가 아닙니다."
        )

    if result.policy_checks_passed:
        raise RuntimeError(
            "현금 부족 시나리오에서 "
            "Policy Checks Passed가 True입니다."
        )

    if result.portfolio_updated:
        raise RuntimeError(
            "현금 부족 시나리오에서 Portfolio가 변경되었습니다."
        )

    assert_close(
        actual=result.updated_cash_balance,
        expected=1_000.0,
        message=(
            "현금 부족 차단 후 Cash Balance가 "
            "변경되었습니다."
        ),
    )

    if result.updated_shares != 0:
        raise RuntimeError(
            "현금 부족 차단 후 Shares가 증가했습니다."
        )

    return result


def validate_add_disabled_scenario(
    symbol: str,
    previous_result: PaperPortfolioResult,
    source_fill: PaperBrokerFillResult,
) -> PaperPortfolioResult:
    """
    추가 매수 금지 정책을 검사합니다.
    """

    add_fill = create_simulated_fill(
        source_fill=source_fill,
        side="BUY",
        quantity=1,
        fill_price=120.0,
    )

    result = run_paper_portfolio_manager(
        symbol=symbol,
        fill_result=add_fill,
        portfolio_state=previous_result.portfolio_state,
        portfolio_policy=PaperPortfolioPolicy(
            allow_add_to_position=False,
        ),
    )

    validate_result_common(
        result
    )

    if result.portfolio_status != "BLOCKED":
        raise RuntimeError(
            "추가 매수 금지 시나리오가 BLOCKED가 아닙니다."
        )

    if result.policy_checks_passed:
        raise RuntimeError(
            "추가 매수 금지 시나리오에서 "
            "Policy Checks Passed가 True입니다."
        )

    if result.portfolio_updated:
        raise RuntimeError(
            "추가 매수 금지 시나리오에서 "
            "Portfolio가 변경되었습니다."
        )

    return result


def validate_partial_exit_disabled_scenario(
    symbol: str,
    previous_result: PaperPortfolioResult,
    source_fill: PaperBrokerFillResult,
) -> PaperPortfolioResult:
    """
    부분 매도 금지 정책을 검사합니다.
    """

    shares = (
        previous_result.portfolio_state.positions[
            symbol
        ].shares
    )

    if shares <= 1:
        raise RuntimeError(
            "부분 매도 금지 테스트에 충분한 Shares가 없습니다."
        )

    sell_fill = create_simulated_fill(
        source_fill=source_fill,
        side="SELL",
        quantity=1,
        fill_price=130.0,
    )

    result = run_paper_portfolio_manager(
        symbol=symbol,
        fill_result=sell_fill,
        portfolio_state=previous_result.portfolio_state,
        portfolio_policy=PaperPortfolioPolicy(
            allow_partial_exit=False,
        ),
    )

    validate_result_common(
        result
    )

    if result.portfolio_status != "BLOCKED":
        raise RuntimeError(
            "부분 매도 금지 시나리오가 BLOCKED가 아닙니다."
        )

    if result.policy_checks_passed:
        raise RuntimeError(
            "부분 매도 금지 시나리오에서 "
            "Policy Checks Passed가 True입니다."
        )

    if result.portfolio_updated:
        raise RuntimeError(
            "부분 매도 금지 시나리오에서 "
            "Portfolio가 변경되었습니다."
        )

    return result


def validate_policy_helper_against_fill(
    portfolio: PaperPortfolioState,
    fill: PaperBrokerFillResult,
    policy: PaperPortfolioPolicy,
) -> None:
    """
    validate_fill_against_policy Helper를 직접 검사합니다.
    """

    position = get_or_create_position(
        portfolio=portfolio,
        symbol=fill.symbol,
    )

    (
        valid,
        errors,
    ) = validate_fill_against_policy(
        portfolio=portfolio,
        position=position,
        fill=fill,
        policy=policy,
    )

    if not valid:
        raise RuntimeError(
            "정상 Fill이 Policy Helper를 통과하지 못했습니다: "
            f"{errors}"
        )

    if errors:
        raise RuntimeError(
            "정상 Fill Policy Helper에서 오류가 생성되었습니다."
        )


def validate_position_metrics_helper() -> None:
    """
    Position Market Value와 Unrealized PnL 계산을 검사합니다.
    """

    position = PaperPosition(
        symbol="AAPL",
        state="LONG",
        shares=10,
        average_price=100.0,
        cost_basis=1_000.0,
        realized_pnl=50.0,
    )

    update_position_metrics(
        position=position,
        latest_price=110.0,
    )

    assert_close(
        actual=position.market_value,
        expected=1_100.0,
        message="Position Market Value가 일치하지 않습니다.",
    )

    assert_close(
        actual=position.unrealized_pnl,
        expected=100.0,
        message="Position Unrealized PnL이 일치하지 않습니다.",
    )

    assert_close(
        actual=position.unrealized_pnl_percent,
        expected=10.0,
        tolerance=0.0001,
        message=(
            "Position Unrealized PnL Percent가 "
            "일치하지 않습니다."
        ),
    )

    flat_position = PaperPosition(
        symbol="MSFT",
        state="FLAT",
        shares=0,
    )

    update_position_metrics(
        position=flat_position,
        latest_price=500.0,
    )

    if flat_position.state != "FLAT":
        raise RuntimeError(
            "Shares가 0인 Position State가 FLAT이 아닙니다."
        )

    assert_close(
        actual=flat_position.market_value,
        expected=0.0,
        message="FLAT Position Market Value가 0이 아닙니다.",
    )


def validate_portfolio_totals_helper() -> None:
    """
    Portfolio 합계 재계산을 검사합니다.
    """

    portfolio = create_empty_portfolio(
        initial_cash=10_000.0
    )

    portfolio.cash_balance = 7_000.0

    portfolio.positions["AAPL"] = PaperPosition(
        symbol="AAPL",
        state="LONG",
        shares=10,
        average_price=100.0,
        cost_basis=1_000.0,
        latest_price=110.0,
        market_value=1_100.0,
        unrealized_pnl=100.0,
        realized_pnl=50.0,
    )

    portfolio.positions["MSFT"] = PaperPosition(
        symbol="MSFT",
        state="LONG",
        shares=5,
        average_price=200.0,
        cost_basis=1_000.0,
        latest_price=220.0,
        market_value=1_100.0,
        unrealized_pnl=100.0,
        realized_pnl=25.0,
    )

    recalculate_portfolio_totals(
        portfolio
    )

    assert_close(
        actual=portfolio.total_market_value,
        expected=2_200.0,
        message="Total Market Value가 일치하지 않습니다.",
    )

    assert_close(
        actual=portfolio.total_unrealized_pnl,
        expected=200.0,
        message="Total Unrealized PnL이 일치하지 않습니다.",
    )

    assert_close(
        actual=portfolio.total_realized_pnl,
        expected=75.0,
        message="Total Realized PnL이 일치하지 않습니다.",
    )

    assert_close(
        actual=portfolio.total_equity,
        expected=9_200.0,
        message="Total Equity가 일치하지 않습니다.",
    )


def validate_duplicate_helper(
    portfolio: PaperPortfolioState,
    fill: PaperBrokerFillResult,
) -> None:
    """
    Duplicate Fill Helper를 검사합니다.
    """

    clean_portfolio = copy_portfolio_state(
        portfolio
    )

    clean_portfolio.processed_fill_ids = []
    clean_portfolio.processed_idempotency_keys = []

    if check_duplicate_fill(
        portfolio=clean_portfolio,
        fill=fill,
    ):
        raise RuntimeError(
            "처리 전 Fill이 Duplicate로 판정되었습니다."
        )

    clean_portfolio.processed_fill_ids.append(
        fill.fill_id
    )

    if not check_duplicate_fill(
        portfolio=clean_portfolio,
        fill=fill,
    ):
        raise RuntimeError(
            "처리된 Fill ID가 Duplicate로 감지되지 않았습니다."
        )

    clean_portfolio.processed_fill_ids = []
    clean_portfolio.processed_idempotency_keys.append(
        fill.idempotency_key
    )

    if not check_duplicate_fill(
        portfolio=clean_portfolio,
        fill=fill,
    ):
        raise RuntimeError(
            "처리된 Idempotency Key가 Duplicate로 "
            "감지되지 않았습니다."
        )


def validate_save_and_load(
    result: PaperPortfolioResult,
) -> tuple[
    Path,
    Path,
    Path,
    PaperPortfolioState,
]:
    """
    V9.9 Result 저장 및 Portfolio State 재로딩을 검사합니다.
    """

    (
        report_path,
        latest_path,
        state_path,
    ) = save_paper_portfolio_result(
        result
    )

    if not report_path.exists():
        raise RuntimeError(
            "V9.9 Report 파일이 생성되지 않았습니다."
        )

    if not latest_path.exists():
        raise RuntimeError(
            "V9.9 Latest 파일이 생성되지 않았습니다."
        )

    if not state_path.exists():
        raise RuntimeError(
            "Portfolio State 파일이 생성되지 않았습니다."
        )

    report_payload = read_json_file(
        report_path
    )

    latest_payload = read_json_file(
        latest_path
    )

    state_payload = read_json_file(
        state_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "Report와 Latest JSON 내용이 일치하지 않습니다."
        )

    if report_payload != result.to_dict():
        raise RuntimeError(
            "저장된 Result JSON이 실행 결과와 "
            "일치하지 않습니다."
        )

    if (
        state_payload
        != result.portfolio_state.to_dict()
    ):
        raise RuntimeError(
            "저장된 Portfolio State JSON이 실행 결과와 "
            "일치하지 않습니다."
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

    if (
        Path(str(report_payload["state_path"]))
        != state_path
    ):
        raise RuntimeError(
            "JSON 내부 State Path가 실제 경로와 "
            "일치하지 않습니다."
        )

    converted_portfolio = portfolio_from_dict(
        state_payload
    )

    if (
        converted_portfolio.to_dict()
        != result.portfolio_state.to_dict()
    ):
        raise RuntimeError(
            "Portfolio Dictionary 변환 결과가 "
            "저장 상태와 일치하지 않습니다."
        )

    loaded_portfolio = load_latest_portfolio_state(
        initial_cash=result.portfolio_state.initial_cash
    )

    if (
        loaded_portfolio.to_dict()
        != result.portfolio_state.to_dict()
    ):
        raise RuntimeError(
            "load_latest_portfolio_state 결과가 "
            "저장 상태와 일치하지 않습니다."
        )

    (
        valid,
        errors,
    ) = validate_portfolio_state(
        loaded_portfolio
    )

    if not valid:
        raise RuntimeError(
            "다시 불러온 Portfolio 상태가 유효하지 않습니다: "
            f"{errors}"
        )

    return (
        report_path,
        latest_path,
        state_path,
        loaded_portfolio,
    )


def print_scenario_summary(
    open_result: PaperPortfolioResult,
    duplicate_result: PaperPortfolioResult,
    add_result: PaperPortfolioResult,
    partial_sell_result: PaperPortfolioResult,
    close_result: PaperPortfolioResult,
    oversell_result: PaperPortfolioResult,
    insufficient_cash_result: PaperPortfolioResult,
    report_path: Path,
    latest_path: Path,
    state_path: Path,
) -> None:
    """
    주요 시나리오 결과를 출력합니다.
    """

    print()
    print("=" * LINE_LENGTH)
    print(
        "V9.9 PAPER PORTFOLIO MANAGER "
        "SCENARIO SUMMARY"
    )
    print("=" * LINE_LENGTH)

    print("OPEN LONG")
    print("-" * LINE_LENGTH)

    print(
        f"Status                         : "
        f"{open_result.portfolio_status}"
    )

    print(
        f"Action                         : "
        f"{open_result.portfolio_action}"
    )

    print(
        f"Cash                           : "
        f"${open_result.updated_cash_balance:,.2f}"
    )

    print(
        f"Shares                         : "
        f"{open_result.updated_shares}"
    )

    print(
        f"Average price                  : "
        f"${open_result.updated_average_price:,.4f}"
    )

    print()
    print("DUPLICATE FILL")
    print("-" * LINE_LENGTH)

    print(
        f"Status                         : "
        f"{duplicate_result.portfolio_status}"
    )

    print(
        f"Action                         : "
        f"{duplicate_result.portfolio_action}"
    )

    print(
        f"Duplicate detected             : "
        f"{duplicate_result.duplicate_fill}"
    )

    print(
        f"Portfolio updated              : "
        f"{duplicate_result.portfolio_updated}"
    )

    print()
    print("ADD LONG")
    print("-" * LINE_LENGTH)

    print(
        f"Status                         : "
        f"{add_result.portfolio_status}"
    )

    print(
        f"Action                         : "
        f"{add_result.portfolio_action}"
    )

    print(
        f"Shares                         : "
        f"{add_result.updated_shares}"
    )

    print(
        f"Average price                  : "
        f"${add_result.updated_average_price:,.4f}"
    )

    print()
    print("PARTIAL SELL")
    print("-" * LINE_LENGTH)

    print(
        f"Status                         : "
        f"{partial_sell_result.portfolio_status}"
    )

    print(
        f"Action                         : "
        f"{partial_sell_result.portfolio_action}"
    )

    print(
        f"Remaining shares               : "
        f"{partial_sell_result.updated_shares}"
    )

    print(
        f"Transaction realized PnL       : "
        f"${partial_sell_result.transaction_realized_pnl:,.2f}"
    )

    print()
    print("CLOSE LONG")
    print("-" * LINE_LENGTH)

    print(
        f"Status                         : "
        f"{close_result.portfolio_status}"
    )

    print(
        f"Action                         : "
        f"{close_result.portfolio_action}"
    )

    print(
        f"Final position state           : "
        f"{close_result.updated_position_state}"
    )

    print(
        f"Final shares                   : "
        f"{close_result.updated_shares}"
    )

    print(
        f"Total realized PnL             : "
        f"${close_result.total_realized_pnl:,.2f}"
    )

    print(
        f"Total equity                   : "
        f"${close_result.total_equity:,.2f}"
    )

    print()
    print("BLOCKED SCENARIOS")
    print("-" * LINE_LENGTH)

    print(
        f"Oversell status                : "
        f"{oversell_result.portfolio_status}"
    )

    print(
        f"Insufficient cash status       : "
        f"{insufficient_cash_result.portfolio_status}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * LINE_LENGTH)

    print(
        f"Broker API called              : "
        f"{close_result.broker_api_called}"
    )

    print(
        f"Live order created             : "
        f"{close_result.live_order_created}"
    )

    print(
        f"Live execution authorized      : "
        f"{close_result.live_execution_authorized}"
    )

    print(
        f"Execution blocked              : "
        f"{close_result.execution_blocked}"
    )

    print()
    print("FILES")
    print("-" * LINE_LENGTH)

    print(
        f"Report file                    : "
        f"{report_path}"
    )

    print(
        f"Latest file                    : "
        f"{latest_path}"
    )

    print(
        f"Portfolio state file           : "
        f"{state_path}"
    )

    print("=" * LINE_LENGTH)


def print_validation_checks(
    open_result: PaperPortfolioResult,
    duplicate_result: PaperPortfolioResult,
    add_result: PaperPortfolioResult,
    partial_sell_result: PaperPortfolioResult,
    close_result: PaperPortfolioResult,
    oversell_result: PaperPortfolioResult,
    insufficient_cash_result: PaperPortfolioResult,
    add_disabled_result: PaperPortfolioResult,
    partial_exit_disabled_result: PaperPortfolioResult,
    loaded_portfolio: PaperPortfolioState,
    report_path: Path,
    latest_path: Path,
    state_path: Path,
) -> None:
    """
    최종 검증 항목을 출력합니다.
    """

    checks = {
        "Version is V9.9": (
            open_result.version == "V9.9"
        ),
        "Open Long status is UPDATED": (
            open_result.portfolio_status
            == "UPDATED"
        ),
        "Open Long action is OPEN_LONG": (
            open_result.portfolio_action
            == "OPEN_LONG"
        ),
        "Open Long position is LONG": (
            open_result.updated_position_state
            == "LONG"
        ),
        "Open Long updated portfolio": (
            open_result.portfolio_updated
        ),
        "Open Long all checks passed": (
            open_result.all_checks_passed
        ),
        "Duplicate status is NO_CHANGE": (
            duplicate_result.portfolio_status
            == "NO_CHANGE"
        ),
        "Duplicate action is NO_ACTION": (
            duplicate_result.portfolio_action
            == "NO_ACTION"
        ),
        "Duplicate fill detected": (
            duplicate_result.duplicate_fill
        ),
        "Duplicate did not update portfolio": (
            not duplicate_result.portfolio_updated
        ),
        "Add Long status is UPDATED": (
            add_result.portfolio_status
            == "UPDATED"
        ),
        "Add Long action is ADD_LONG": (
            add_result.portfolio_action
            == "ADD_LONG"
        ),
        "Partial Sell status is UPDATED": (
            partial_sell_result.portfolio_status
            == "UPDATED"
        ),
        "Partial Sell action is REDUCE_LONG": (
            partial_sell_result.portfolio_action
            == "REDUCE_LONG"
        ),
        "Partial Sell leaves LONG position": (
            partial_sell_result.updated_position_state
            == "LONG"
        ),
        "Close Long status is UPDATED": (
            close_result.portfolio_status
            == "UPDATED"
        ),
        "Close Long action is CLOSE_LONG": (
            close_result.portfolio_action
            == "CLOSE_LONG"
        ),
        "Close Long position is FLAT": (
            close_result.updated_position_state
            == "FLAT"
        ),
        "Close Long shares are zero": (
            close_result.updated_shares == 0
        ),
        "Close Long cost basis is zero": (
            abs(
                close_result.updated_cost_basis
            )
            <= 0.01
        ),
        "Oversell status is BLOCKED": (
            oversell_result.portfolio_status
            == "BLOCKED"
        ),
        "Oversell did not update portfolio": (
            not oversell_result.portfolio_updated
        ),
        "Insufficient cash is BLOCKED": (
            insufficient_cash_result.portfolio_status
            == "BLOCKED"
        ),
        "Insufficient cash did not update portfolio": (
            not insufficient_cash_result.portfolio_updated
        ),
        "Add disabled scenario is BLOCKED": (
            add_disabled_result.portfolio_status
            == "BLOCKED"
        ),
        "Partial exit disabled is BLOCKED": (
            partial_exit_disabled_result.portfolio_status
            == "BLOCKED"
        ),
        "Broker API was not called": (
            not close_result.broker_api_called
        ),
        "Live order was not created": (
            not close_result.live_order_created
        ),
        "Live execution was not authorized": (
            not close_result.live_execution_authorized
        ),
        "Execution remains blocked": (
            close_result.execution_blocked
        ),
        "Loaded portfolio matches saved state": (
            loaded_portfolio.to_dict()
            == close_result.portfolio_state.to_dict()
        ),
        "Report file exists": (
            report_path.exists()
        ),
        "Latest file exists": (
            latest_path.exists()
        ),
        "State file exists": (
            state_path.exists()
        ),
        "Reasons exist": bool(
            close_result.reasons
        ),
        "Warnings exist": bool(
            close_result.warnings
        ),
        "Next actions exist": bool(
            close_result.next_actions
        ),
    }

    print()
    print("=" * LINE_LENGTH)
    print("VALIDATION CHECKS")
    print("=" * LINE_LENGTH)

    for name, value in checks.items():
        print_check(
            name,
            value,
        )

    print("=" * LINE_LENGTH)

    failed_checks = [
        name
        for name, value in checks.items()
        if not value
    ]

    if failed_checks:
        raise RuntimeError(
            "다음 V9.9 검증 항목이 실패했습니다: "
            f"{failed_checks}"
        )


def main() -> None:
    """
    V9.9 Paper Portfolio Manager 통합 테스트입니다.

    검증 항목:

    1. 기본 Policy 구조 및 불변성
    2. 잘못된 Policy 차단
    3. 신규 Portfolio 생성
    4. Position Helper 검사
    5. Portfolio Action 결정 규칙
    6. BUY 및 SELL 계산 Helper
    7. OPEN_LONG
    8. Duplicate Fill 차단
    9. ADD_LONG
    10. 부분 매도 REDUCE_LONG
    11. 전체 매도 CLOSE_LONG
    12. 보유 수량 초과 매도 차단
    13. 현금 부족 매수 차단
    14. 추가 매수 금지 정책
    15. 부분 매도 금지 정책
    16. JSON 저장 및 재로딩
    17. 실제 Broker와 Live Execution 차단
    """

    symbol = "AAPL"
    initial_cash = 10_000.0

    print_header()

    try:
        policy = PaperPortfolioPolicy()

        validate_policy_structure(
            policy
        )

        validate_policy_is_immutable(
            policy
        )

        validate_invalid_policies()

        empty_portfolio = create_empty_portfolio(
            initial_cash=initial_cash
        )

        validate_empty_portfolio(
            portfolio=empty_portfolio,
            expected_cash=initial_cash,
        )

        validate_position_helpers(
            symbol=symbol
        )

        validate_action_rules()

        validate_position_metrics_helper()

        validate_portfolio_totals_helper()

        source_fill = create_normal_source_fill(
            symbol=symbol,
            initial_cash=initial_cash,
        )

        validate_calculation_helpers(
            source_fill=source_fill
        )

        first_buy_fill = create_simulated_fill(
            source_fill=source_fill,
            side="BUY",
            quantity=4,
            fill_price=100.0,
            commission=1.0,
            symbol=symbol,
        )

        (
            first_fill_valid,
            first_fill_errors,
        ) = validate_paper_fill(
            first_buy_fill
        )

        if not first_fill_valid:
            raise RuntimeError(
                "첫 번째 BUY Fill이 유효하지 않습니다: "
                f"{first_fill_errors}"
            )

        validate_policy_helper_against_fill(
            portfolio=empty_portfolio,
            fill=first_buy_fill,
            policy=policy,
        )

        validate_duplicate_helper(
            portfolio=empty_portfolio,
            fill=first_buy_fill,
        )

        open_result = validate_open_long_scenario(
            symbol=symbol,
            initial_cash=initial_cash,
            fill=first_buy_fill,
        )

        duplicate_result = validate_duplicate_scenario(
            symbol=symbol,
            original_result=open_result,
            original_fill=first_buy_fill,
        )

        add_disabled_result = (
            validate_add_disabled_scenario(
                symbol=symbol,
                previous_result=open_result,
                source_fill=source_fill,
            )
        )

        second_buy_fill = create_simulated_fill(
            source_fill=source_fill,
            side="BUY",
            quantity=2,
            fill_price=110.0,
            commission=1.0,
            symbol=symbol,
        )

        add_result = validate_add_long_scenario(
            symbol=symbol,
            previous_result=open_result,
            fill=second_buy_fill,
        )

        partial_exit_disabled_result = (
            validate_partial_exit_disabled_scenario(
                symbol=symbol,
                previous_result=add_result,
                source_fill=source_fill,
            )
        )

        partial_sell_fill = create_simulated_fill(
            source_fill=source_fill,
            side="SELL",
            quantity=2,
            fill_price=120.0,
            commission=1.0,
            symbol=symbol,
        )

        partial_sell_result = (
            validate_partial_sell_scenario(
                symbol=symbol,
                previous_result=add_result,
                sell_fill=partial_sell_fill,
            )
        )

        oversell_result = validate_oversell_scenario(
            symbol=symbol,
            source_portfolio=(
                partial_sell_result.portfolio_state
            ),
            source_fill=source_fill,
        )

        remaining_shares = (
            partial_sell_result.portfolio_state.positions[
                symbol
            ].shares
        )

        close_sell_fill = create_simulated_fill(
            source_fill=source_fill,
            side="SELL",
            quantity=remaining_shares,
            fill_price=125.0,
            commission=1.0,
            symbol=symbol,
        )

        close_result = validate_close_long_scenario(
            symbol=symbol,
            previous_result=partial_sell_result,
            sell_fill=close_sell_fill,
        )

        insufficient_cash_result = (
            validate_insufficient_cash_scenario(
                symbol=symbol,
                source_fill=source_fill,
            )
        )

        (
            report_path,
            latest_path,
            state_path,
            loaded_portfolio,
        ) = validate_save_and_load(
            close_result
        )

        print_scenario_summary(
            open_result=open_result,
            duplicate_result=duplicate_result,
            add_result=add_result,
            partial_sell_result=partial_sell_result,
            close_result=close_result,
            oversell_result=oversell_result,
            insufficient_cash_result=(
                insufficient_cash_result
            ),
            report_path=report_path,
            latest_path=latest_path,
            state_path=state_path,
        )

        print_validation_checks(
            open_result=open_result,
            duplicate_result=duplicate_result,
            add_result=add_result,
            partial_sell_result=partial_sell_result,
            close_result=close_result,
            oversell_result=oversell_result,
            insufficient_cash_result=(
                insufficient_cash_result
            ),
            add_disabled_result=add_disabled_result,
            partial_exit_disabled_result=(
                partial_exit_disabled_result
            ),
            loaded_portfolio=loaded_portfolio,
            report_path=report_path,
            latest_path=latest_path,
            state_path=state_path,
        )

        print()
        print(
            "V9.9 paper portfolio manager "
            "test completed successfully."
        )

        print(
            "신규 매수 OPEN_LONG과 추가 매수 ADD_LONG이 "
            "정상 처리되었습니다."
        )

        print(
            "부분 매도 REDUCE_LONG과 전체 매도 CLOSE_LONG이 "
            "정상 처리되었습니다."
        )

        print(
            "중복 Fill, 보유 수량 초과 매도 및 "
            "현금 부족 매수는 정상 차단되었습니다."
        )

        print(
            "Portfolio Result와 최신 Portfolio State가 "
            "JSON 파일로 정상 저장되고 다시 로딩되었습니다."
        )

        print(
            "실제 Broker API, 실제 주문 및 Live Execution은 "
            "모두 차단되었습니다."
        )

        print(
            "주의: 이 테스트는 연구용 Paper Trading "
            "가상 계좌 테스트이며 실제 증권 거래가 아닙니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * LINE_LENGTH)
        print("V9.9 TEST CANCELLED")
        print("=" * LINE_LENGTH)

        print(
            "사용자가 V9.9 Paper Portfolio Manager "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * LINE_LENGTH)
        print(
            "V9.9 PAPER PORTFOLIO MANAGER ERROR"
        )
        print("=" * LINE_LENGTH)

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