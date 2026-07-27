import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd

from backtest.paper_portfolio_manager import (
    PaperPortfolioState,
    PaperPosition,
    create_empty_portfolio,
    recalculate_portfolio_totals,
    validate_portfolio_state,
)
from backtest.paper_portfolio_valuation import (
    PAPER_VALUATION_OUTPUT_DIRECTORY,
    VALID_POSITION_VALUATION_STATUSES,
    VALID_PRICE_SOURCES,
    VALID_VALUATION_STATUSES,
    PaperPortfolioValuationPolicy,
    PaperPortfolioValuationResult,
    PaperPositionValuation,
    calculate_portfolio_weights,
    calculate_position_valuation,
    extract_latest_close,
    load_latest_valuation_result,
    load_valuation_portfolio_state,
    normalize_provided_prices,
    normalize_symbol,
    recalculate_valued_portfolio_totals,
    resolve_latest_price,
    round_money,
    round_percent,
    round_price,
    run_paper_portfolio_valuation,
    save_paper_portfolio_valuation,
    update_portfolio_position,
    validate_market_price,
    validate_valuation_policy,
)


LINE_LENGTH = 140
SYMBOL = "AAPL"
INITIAL_CASH = 10_000.0


def print_header() -> None:
    """
    V10.0 테스트 제목을 출력합니다.
    """

    print()
    print("=" * LINE_LENGTH)
    print(
        "AI STOCK BOT V10.0 "
        "PAPER PORTFOLIO VALUATION TEST"
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
        f"{name:<60}: {value}"
    )


def assert_close(
    actual: float,
    expected: float,
    tolerance: float = 0.01,
    message: str = "숫자 값이 일치하지 않습니다.",
) -> None:
    """
    두 숫자가 허용 오차 이내인지 확인합니다.
    """

    difference = abs(
        float(actual)
        - float(expected)
    )

    if difference > tolerance:
        raise RuntimeError(
            f"{message} "
            f"Actual={actual}, "
            f"Expected={expected}, "
            f"Difference={difference}"
        )


def read_json_file(
    file_path: Path,
) -> dict[str, Any]:
    """
    JSON 파일을 읽습니다.
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


def create_test_portfolio(
    symbol: str = SYMBOL,
    initial_cash: float = INITIAL_CASH,
    cash_balance: float = 8_000.0,
    shares: int = 10,
    average_price: float = 200.0,
    latest_price: float = 200.0,
    realized_pnl: float = 0.0,
    total_commission: float = 0.0,
) -> PaperPortfolioState:
    """
    V10.0 평가에 사용할 Long Position Portfolio를 만듭니다.

    실제 계좌나 Broker에는 연결되지 않습니다.
    """

    if shares <= 0:
        raise ValueError(
            "Long Position 테스트의 shares는 "
            "0보다 커야 합니다."
        )

    normalized_symbol = normalize_symbol(
        symbol
    )

    portfolio = create_empty_portfolio(
        initial_cash=initial_cash
    )

    cost_basis = round_money(
        shares
        * average_price
    )

    market_value = round_money(
        shares
        * latest_price
    )

    unrealized_pnl = round_money(
        market_value
        - cost_basis
    )

    if cost_basis > 0:
        unrealized_pnl_percent = round_percent(
            (
                unrealized_pnl
                / cost_basis
            )
            * 100.0
        )

    else:
        unrealized_pnl_percent = 0.0

    position = PaperPosition(
        symbol=normalized_symbol,
        state="LONG",
        shares=shares,
        average_price=round_price(
            average_price
        ),
        cost_basis=cost_basis,
        latest_price=round_price(
            latest_price
        ),
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_percent=(
            unrealized_pnl_percent
        ),
        realized_pnl=round_money(
            realized_pnl
        ),
    )

    portfolio.cash_balance = round_money(
        cash_balance
    )

    portfolio.positions[
        normalized_symbol
    ] = position

    portfolio.total_commission = round_money(
        total_commission
    )

    recalculate_portfolio_totals(
        portfolio
    )

    (
        valid,
        errors,
    ) = validate_portfolio_state(
        portfolio
    )

    if not valid:
        raise RuntimeError(
            "생성된 테스트 Portfolio가 "
            f"유효하지 않습니다: {errors}"
        )

    return portfolio


def add_second_position(
    portfolio: PaperPortfolioState,
    symbol: str = "MSFT",
    shares: int = 5,
    average_price: float = 300.0,
    latest_price: float = 300.0,
) -> None:
    """
    Partial Valuation 테스트를 위해 두 번째 Position을 추가합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    cost_basis = round_money(
        shares
        * average_price
    )

    market_value = round_money(
        shares
        * latest_price
    )

    unrealized_pnl = round_money(
        market_value
        - cost_basis
    )

    if cost_basis > 0:
        unrealized_pnl_percent = round_percent(
            (
                unrealized_pnl
                / cost_basis
            )
            * 100.0
        )

    else:
        unrealized_pnl_percent = 0.0

    portfolio.positions[
        normalized_symbol
    ] = PaperPosition(
        symbol=normalized_symbol,
        state="LONG",
        shares=shares,
        average_price=round_price(
            average_price
        ),
        cost_basis=cost_basis,
        latest_price=round_price(
            latest_price
        ),
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_percent=(
            unrealized_pnl_percent
        ),
        realized_pnl=0.0,
    )

    recalculate_portfolio_totals(
        portfolio
    )


def validate_policy_structure() -> (
    PaperPortfolioValuationPolicy
):
    """
    기본 V10.0 정책 구조를 검사합니다.
    """

    policy = PaperPortfolioValuationPolicy()

    if not isinstance(
        policy,
        PaperPortfolioValuationPolicy,
    ):
        raise RuntimeError(
            "Policy 형식이 올바르지 않습니다."
        )

    (
        valid,
        errors,
    ) = validate_valuation_policy(
        policy
    )

    if not valid:
        raise RuntimeError(
            "기본 Valuation Policy가 "
            f"유효하지 않습니다: {errors}"
        )

    if errors:
        raise RuntimeError(
            "정상 Policy 검사에서 오류 메시지가 "
            "생성되었습니다."
        )

    expected_keys = {
        "require_all_prices",
        "allow_position_price_fallback",
        "allow_zero_position_price",
        "minimum_valid_price",
        "maximum_valid_price",
        "price_period",
        "price_interval",
        "cash_weight_warning_percent",
        "invested_weight_warning_percent",
        "paper_only",
        "live_execution_disabled",
    }

    actual_keys = set(
        policy.to_dict().keys()
    )

    if actual_keys != expected_keys:
        raise RuntimeError(
            "Valuation Policy Dictionary 구조가 "
            "예상 결과와 일치하지 않습니다."
        )

    return policy


def validate_policy_immutable(
    policy: PaperPortfolioValuationPolicy,
) -> None:
    """
    Valuation Policy가 Frozen Dataclass인지 검사합니다.
    """

    immutable = False

    try:
        policy.minimum_valid_price = 10.0

    except (
        FrozenInstanceError,
        AttributeError,
    ):
        immutable = True

    if not immutable:
        raise RuntimeError(
            "Valuation Policy 값을 직접 변경할 수 있습니다."
        )


def validate_invalid_policies() -> None:
    """
    잘못된 V10.0 정책이 거부되는지 검사합니다.
    """

    invalid_policies = [
        PaperPortfolioValuationPolicy(
            minimum_valid_price=0.0,
        ),
        PaperPortfolioValuationPolicy(
            minimum_valid_price=-1.0,
        ),
        PaperPortfolioValuationPolicy(
            maximum_valid_price=0.0,
        ),
        PaperPortfolioValuationPolicy(
            minimum_valid_price=100.0,
            maximum_valid_price=50.0,
        ),
        PaperPortfolioValuationPolicy(
            cash_weight_warning_percent=-1.0,
        ),
        PaperPortfolioValuationPolicy(
            cash_weight_warning_percent=101.0,
        ),
        PaperPortfolioValuationPolicy(
            invested_weight_warning_percent=-1.0,
        ),
        PaperPortfolioValuationPolicy(
            invested_weight_warning_percent=101.0,
        ),
        PaperPortfolioValuationPolicy(
            price_period="",
        ),
        PaperPortfolioValuationPolicy(
            price_interval="",
        ),
        PaperPortfolioValuationPolicy(
            paper_only=False,
        ),
        PaperPortfolioValuationPolicy(
            live_execution_disabled=False,
        ),
    ]

    for index, policy in enumerate(
        invalid_policies,
        start=1,
    ):
        (
            valid,
            errors,
        ) = validate_valuation_policy(
            policy
        )

        if valid:
            raise RuntimeError(
                f"Invalid Policy #{index}가 "
                "유효한 것으로 판정되었습니다."
            )

        if not errors:
            raise RuntimeError(
                f"Invalid Policy #{index} 검사에서 "
                "오류 메시지가 생성되지 않았습니다."
            )


def validate_utility_functions() -> None:
    """
    Symbol, 가격 및 반올림 Helper를 검사합니다.
    """

    if normalize_symbol(
        " aapl "
    ) != "AAPL":
        raise RuntimeError(
            "Symbol 정규화 결과가 올바르지 않습니다."
        )

    try:
        normalize_symbol(
            "   "
        )

    except ValueError:
        pass

    else:
        raise RuntimeError(
            "빈 Symbol이 거부되지 않았습니다."
        )

    assert_close(
        actual=round_money(
            10.126
        ),
        expected=10.13,
        tolerance=0.000001,
        message="round_money 결과가 올바르지 않습니다.",
    )

    assert_close(
        actual=round_price(
            10.123456
        ),
        expected=10.1235,
        tolerance=0.000001,
        message="round_price 결과가 올바르지 않습니다.",
    )

    assert_close(
        actual=round_percent(
            12.345678
        ),
        expected=12.3457,
        tolerance=0.000001,
        message="round_percent 결과가 올바르지 않습니다.",
    )


def validate_market_price_rules(
    policy: PaperPortfolioValuationPolicy,
) -> None:
    """
    정상·0·음수·과도한 가격 검사를 수행합니다.
    """

    (
        normal_valid,
        normal_errors,
    ) = validate_market_price(
        price=250.0,
        policy=policy,
    )

    if not normal_valid:
        raise RuntimeError(
            "정상 시장가격이 거부되었습니다: "
            f"{normal_errors}"
        )

    (
        zero_valid,
        zero_errors,
    ) = validate_market_price(
        price=0.0,
        policy=policy,
    )

    if zero_valid:
        raise RuntimeError(
            "0 가격이 유효한 것으로 판정되었습니다."
        )

    if not zero_errors:
        raise RuntimeError(
            "0 가격 검사에서 오류가 생성되지 않았습니다."
        )

    (
        negative_valid,
        negative_errors,
    ) = validate_market_price(
        price=-10.0,
        policy=policy,
    )

    if negative_valid:
        raise RuntimeError(
            "음수 가격이 유효한 것으로 판정되었습니다."
        )

    if not negative_errors:
        raise RuntimeError(
            "음수 가격 검사에서 오류가 생성되지 않았습니다."
        )

    (
        high_valid,
        high_errors,
    ) = validate_market_price(
        price=2_000_000.0,
        policy=policy,
    )

    if high_valid:
        raise RuntimeError(
            "Maximum 가격 초과 값이 "
            "유효한 것으로 판정되었습니다."
        )

    if not high_errors:
        raise RuntimeError(
            "Maximum 가격 검사에서 오류가 생성되지 않았습니다."
        )

    zero_allowed_policy = (
        PaperPortfolioValuationPolicy(
            allow_zero_position_price=True,
        )
    )

    (
        zero_allowed_valid,
        zero_allowed_errors,
    ) = validate_market_price(
        price=0.0,
        policy=zero_allowed_policy,
    )

    if not zero_allowed_valid:
        raise RuntimeError(
            "0 가격 허용 정책에서 가격이 거부되었습니다: "
            f"{zero_allowed_errors}"
        )


def validate_dataframe_price_extraction() -> None:
    """
    DataFrame에서 최신 Close 추출을 검사합니다.
    """

    history = pd.DataFrame(
        {
            "Close": [
                100.0,
                105.0,
                110.25,
            ]
        }
    )

    latest_close = extract_latest_close(
        history
    )

    assert_close(
        actual=latest_close,
        expected=110.25,
        tolerance=0.0001,
        message="최신 Close 추출 결과가 일치하지 않습니다.",
    )

    history_with_nan = pd.DataFrame(
        {
            "Close": [
                100.0,
                None,
                115.5,
                None,
            ]
        }
    )

    latest_non_null_close = (
        extract_latest_close(
            history_with_nan
        )
    )

    assert_close(
        actual=latest_non_null_close,
        expected=115.5,
        tolerance=0.0001,
        message="최신 유효 Close 추출 결과가 다릅니다.",
    )

    invalid_dataframes = [
        pd.DataFrame(),
        pd.DataFrame(
            {
                "Open": [
                    100.0,
                ]
            }
        ),
        pd.DataFrame(
            {
                "Close": [
                    None,
                    None,
                ]
            }
        ),
    ]

    for dataframe in invalid_dataframes:
        try:
            extract_latest_close(
                dataframe
            )

        except (
            RuntimeError,
            TypeError,
        ):
            pass

        else:
            raise RuntimeError(
                "잘못된 Market History가 "
                "거부되지 않았습니다."
            )


def validate_price_normalization() -> None:
    """
    사용자가 제공한 가격 Dictionary를 검사합니다.
    """

    normalized = normalize_provided_prices(
        {
            " aapl ": 250.123456,
            "msft": 500.56789,
        }
    )

    if set(
        normalized.keys()
    ) != {
        "AAPL",
        "MSFT",
    }:
        raise RuntimeError(
            "제공 가격 Symbol 정규화가 실패했습니다."
        )

    assert_close(
        actual=normalized["AAPL"],
        expected=250.1235,
        tolerance=0.0001,
        message="AAPL 제공 가격 반올림이 다릅니다.",
    )

    assert_close(
        actual=normalized["MSFT"],
        expected=500.5679,
        tolerance=0.0001,
        message="MSFT 제공 가격 반올림이 다릅니다.",
    )

    if normalize_provided_prices(
        None
    ) != {}:
        raise RuntimeError(
            "None 가격 입력이 빈 Dictionary가 아닙니다."
        )

    try:
        normalize_provided_prices(
            {
                "AAPL": "invalid",
            }
        )

    except ValueError:
        pass

    else:
        raise RuntimeError(
            "잘못된 제공 가격이 거부되지 않았습니다."
        )


def validate_price_resolution(
    portfolio: PaperPortfolioState,
    policy: PaperPortfolioValuationPolicy,
) -> None:
    """
    제공 가격과 Position 가격 Fallback을 검사합니다.
    """

    position = portfolio.positions[
        SYMBOL
    ]

    (
        provided_price,
        provided_source,
        provided_label,
        provided_errors,
    ) = resolve_latest_price(
        symbol=SYMBOL,
        position=position,
        provided_prices={
            SYMBOL: 250.0,
        },
        policy=policy,
    )

    assert_close(
        actual=provided_price or 0.0,
        expected=250.0,
        tolerance=0.0001,
        message="제공 가격 Resolve 결과가 다릅니다.",
    )

    if provided_source != "PROVIDED":
        raise RuntimeError(
            "제공 가격 Source가 PROVIDED가 아닙니다."
        )

    if not provided_label:
        raise RuntimeError(
            "제공 가격 Source Label이 없습니다."
        )

    if provided_errors:
        raise RuntimeError(
            "제공 가격 Resolve에서 오류가 생성되었습니다."
        )

    fallback_policy = (
        PaperPortfolioValuationPolicy(
            allow_position_price_fallback=True,
        )
    )

    with patch(
        "backtest.paper_portfolio_valuation."
        "fetch_latest_market_price",
        side_effect=RuntimeError(
            "테스트용 시장가격 조회 실패"
        ),
    ):
        (
            fallback_price,
            fallback_source,
            fallback_label,
            fallback_errors,
        ) = resolve_latest_price(
            symbol=SYMBOL,
            position=position,
            provided_prices={},
            policy=fallback_policy,
        )

    assert_close(
        actual=fallback_price or 0.0,
        expected=position.latest_price,
        tolerance=0.0001,
        message="Position Price Fallback 값이 다릅니다.",
    )

    if fallback_source != "POSITION_PRICE":
        raise RuntimeError(
            "Fallback Source가 POSITION_PRICE가 아닙니다."
        )

    if not fallback_label:
        raise RuntimeError(
            "Fallback Source Label이 없습니다."
        )

    if not fallback_errors:
        raise RuntimeError(
            "시장가격 조회 실패 경고가 기록되지 않았습니다."
        )


def validate_position_valuation_calculation(
    portfolio: PaperPortfolioState,
    policy: PaperPortfolioValuationPolicy,
) -> None:
    """
    단일 Long Position의 평가 계산을 검사합니다.
    """

    position = portfolio.positions[
        SYMBOL
    ]

    valuation = calculate_position_valuation(
        position=position,
        latest_price=250.0,
        price_source="PROVIDED",
        price_source_label="테스트 제공 가격",
        policy=policy,
    )

    if not isinstance(
        valuation,
        PaperPositionValuation,
    ):
        raise RuntimeError(
            "Position Valuation 형식이 올바르지 않습니다."
        )

    if valuation.valuation_status != "VALUED":
        raise RuntimeError(
            "Position Valuation Status가 VALUED가 아닙니다."
        )

    if valuation.price_source != "PROVIDED":
        raise RuntimeError(
            "Position Price Source가 PROVIDED가 아닙니다."
        )

    if valuation.shares != 10:
        raise RuntimeError(
            "Position Shares가 10이 아닙니다."
        )

    assert_close(
        actual=valuation.market_value,
        expected=2_500.0,
        message="Position Market Value가 다릅니다.",
    )

    assert_close(
        actual=valuation.unrealized_pnl,
        expected=500.0,
        message="Position Unrealized PnL이 다릅니다.",
    )

    assert_close(
        actual=valuation.unrealized_pnl_percent,
        expected=25.0,
        tolerance=0.0001,
        message="Position Unrealized PnL %가 다릅니다.",
    )

    assert_close(
        actual=valuation.price_change,
        expected=50.0,
        tolerance=0.0001,
        message="Position Price Change가 다릅니다.",
    )

    assert_close(
        actual=valuation.price_change_percent,
        expected=25.0,
        tolerance=0.0001,
        message="Position Price Change %가 다릅니다.",
    )

    if not valuation.price_loaded:
        raise RuntimeError(
            "Position Price Loaded가 False입니다."
        )

    if not valuation.price_valid:
        raise RuntimeError(
            "Position Price Valid가 False입니다."
        )

    if not valuation.valuation_calculated:
        raise RuntimeError(
            "Position Valuation Calculated가 False입니다."
        )

    if not valuation.checks_passed:
        raise RuntimeError(
            "Position Checks Passed가 False입니다."
        )


def validate_flat_position_calculation(
    policy: PaperPortfolioValuationPolicy,
) -> None:
    """
    FLAT Position 평가를 검사합니다.
    """

    position = PaperPosition(
        symbol="AAPL",
        state="FLAT",
        shares=0,
        average_price=0.0,
        cost_basis=0.0,
        latest_price=125.0,
        market_value=0.0,
        unrealized_pnl=0.0,
        unrealized_pnl_percent=0.0,
        realized_pnl=100.0,
    )

    valuation = calculate_position_valuation(
        position=position,
        latest_price=None,
        price_source="NOT_REQUIRED",
        price_source_label=(
            "FLAT Position 가격 불필요"
        ),
        policy=policy,
    )

    if valuation.valuation_status != "FLAT":
        raise RuntimeError(
            "FLAT Position Status가 FLAT이 아닙니다."
        )

    if valuation.price_source != "NOT_REQUIRED":
        raise RuntimeError(
            "FLAT Position Price Source가 "
            "NOT_REQUIRED가 아닙니다."
        )

    if valuation.shares != 0:
        raise RuntimeError(
            "FLAT Position Shares가 0이 아닙니다."
        )

    assert_close(
        actual=valuation.market_value,
        expected=0.0,
        message="FLAT Position Market Value가 0이 아닙니다.",
    )

    assert_close(
        actual=valuation.unrealized_pnl,
        expected=0.0,
        message="FLAT Position Unrealized PnL이 0이 아닙니다.",
    )

    assert_close(
        actual=valuation.realized_pnl,
        expected=100.0,
        message="FLAT Position Realized PnL이 다릅니다.",
    )


def validate_missing_price_calculation(
    portfolio: PaperPortfolioState,
    policy: PaperPortfolioValuationPolicy,
) -> None:
    """
    최신 가격이 없을 때 PRICE_MISSING을 검사합니다.
    """

    position = portfolio.positions[
        SYMBOL
    ]

    valuation = calculate_position_valuation(
        position=position,
        latest_price=None,
        price_source="UNAVAILABLE",
        price_source_label="가격 없음",
        policy=policy,
        resolution_errors=[
            "테스트용 가격 조회 실패",
        ],
    )

    if valuation.valuation_status != "PRICE_MISSING":
        raise RuntimeError(
            "누락 가격 Status가 PRICE_MISSING이 아닙니다."
        )

    if valuation.price_loaded:
        raise RuntimeError(
            "누락 가격에서 Price Loaded가 True입니다."
        )

    if valuation.price_valid:
        raise RuntimeError(
            "누락 가격에서 Price Valid가 True입니다."
        )

    if valuation.valuation_calculated:
        raise RuntimeError(
            "누락 가격에서 Valuation Calculated가 True입니다."
        )

    if valuation.checks_passed:
        raise RuntimeError(
            "누락 가격에서 Checks Passed가 True입니다."
        )

    assert_close(
        actual=valuation.market_value,
        expected=position.market_value,
        message=(
            "누락 가격에서 기존 Market Value가 "
            "유지되지 않았습니다."
        ),
    )


def validate_invalid_price_calculation(
    portfolio: PaperPortfolioState,
    policy: PaperPortfolioValuationPolicy,
) -> None:
    """
    0 가격의 INVALID_PRICE 결과를 검사합니다.
    """

    position = portfolio.positions[
        SYMBOL
    ]

    valuation = calculate_position_valuation(
        position=position,
        latest_price=0.0,
        price_source="PROVIDED",
        price_source_label="테스트 0 가격",
        policy=policy,
    )

    if valuation.valuation_status != "INVALID_PRICE":
        raise RuntimeError(
            "0 가격 Status가 INVALID_PRICE가 아닙니다."
        )

    if not valuation.price_loaded:
        raise RuntimeError(
            "0 가격에서 Price Loaded가 False입니다."
        )

    if valuation.price_valid:
        raise RuntimeError(
            "0 가격에서 Price Valid가 True입니다."
        )

    if valuation.valuation_calculated:
        raise RuntimeError(
            "0 가격에서 Valuation Calculated가 True입니다."
        )

    if valuation.checks_passed:
        raise RuntimeError(
            "0 가격에서 Checks Passed가 True입니다."
        )


def validate_weight_calculation() -> None:
    """
    Portfolio Weight 계산을 검사합니다.
    """

    valuations = {
        "AAPL": PaperPositionValuation(
            symbol="AAPL",
            valuation_status="VALUED",
            valuation_status_label="평가 완료",
            position_state="LONG",
            shares=10,
            average_price=100.0,
            cost_basis=1_000.0,
            previous_price=100.0,
            latest_price=120.0,
            price_change=20.0,
            price_change_percent=20.0,
            price_source="PROVIDED",
            price_source_label="제공 가격",
            previous_market_value=1_000.0,
            market_value=1_200.0,
            market_value_change=200.0,
            unrealized_pnl=200.0,
            unrealized_pnl_percent=20.0,
            realized_pnl=0.0,
            portfolio_weight_percent=0.0,
            price_loaded=True,
            price_valid=True,
            valuation_calculated=True,
            checks_passed=True,
        ),
        "MSFT": PaperPositionValuation(
            symbol="MSFT",
            valuation_status="VALUED",
            valuation_status_label="평가 완료",
            position_state="LONG",
            shares=5,
            average_price=200.0,
            cost_basis=1_000.0,
            previous_price=200.0,
            latest_price=240.0,
            price_change=40.0,
            price_change_percent=20.0,
            price_source="PROVIDED",
            price_source_label="제공 가격",
            previous_market_value=1_000.0,
            market_value=1_200.0,
            market_value_change=200.0,
            unrealized_pnl=200.0,
            unrealized_pnl_percent=20.0,
            realized_pnl=0.0,
            portfolio_weight_percent=0.0,
            price_loaded=True,
            price_valid=True,
            valuation_calculated=True,
            checks_passed=True,
        ),
    }

    (
        cash_weight,
        invested_weight,
    ) = calculate_portfolio_weights(
        position_valuations=valuations,
        total_equity=10_000.0,
        cash_balance=7_600.0,
    )

    assert_close(
        actual=cash_weight,
        expected=76.0,
        tolerance=0.0001,
        message="Cash Weight가 다릅니다.",
    )

    assert_close(
        actual=invested_weight,
        expected=24.0,
        tolerance=0.0001,
        message="Invested Weight가 다릅니다.",
    )

    assert_close(
        actual=valuations["AAPL"].portfolio_weight_percent,
        expected=12.0,
        tolerance=0.0001,
        message="AAPL Weight가 다릅니다.",
    )

    assert_close(
        actual=valuations["MSFT"].portfolio_weight_percent,
        expected=12.0,
        tolerance=0.0001,
        message="MSFT Weight가 다릅니다.",
    )


def validate_result_common(
    result: PaperPortfolioValuationResult,
) -> None:
    """
    모든 V10.0 결과의 공통 구조를 검사합니다.
    """

    if not isinstance(
        result,
        PaperPortfolioValuationResult,
    ):
        raise RuntimeError(
            "결과 형식이 "
            "PaperPortfolioValuationResult가 아닙니다."
        )

    if result.version != "V10.0":
        raise RuntimeError(
            f"Version이 V10.0이 아닙니다: {result.version}"
        )

    if not result.valuation_id:
        raise RuntimeError(
            "Valuation ID가 비어 있습니다."
        )

    if not result.portfolio_id:
        raise RuntimeError(
            "Portfolio ID가 비어 있습니다."
        )

    if (
        result.valuation_status
        not in VALID_VALUATION_STATUSES
    ):
        raise RuntimeError(
            "Valuation Status가 유효하지 않습니다."
        )

    if not isinstance(
        result.valuation_policy,
        PaperPortfolioValuationPolicy,
    ):
        raise RuntimeError(
            "Result Policy 형식이 올바르지 않습니다."
        )

    if not isinstance(
        result.updated_portfolio_state,
        PaperPortfolioState,
    ):
        raise RuntimeError(
            "Updated Portfolio State 형식이 올바르지 않습니다."
        )

    for symbol, valuation in (
        result.position_valuations.items()
    ):
        if symbol != normalize_symbol(
            symbol
        ):
            raise RuntimeError(
                "Position Valuation Symbol이 "
                "정규화되지 않았습니다."
            )

        if not isinstance(
            valuation,
            PaperPositionValuation,
        ):
            raise RuntimeError(
                "Position Valuation 형식이 올바르지 않습니다."
            )

        if (
            valuation.valuation_status
            not in VALID_POSITION_VALUATION_STATUSES
        ):
            raise RuntimeError(
                "Position Valuation Status가 유효하지 않습니다."
            )

        if (
            valuation.price_source
            not in VALID_PRICE_SOURCES
        ):
            raise RuntimeError(
                "Position Price Source가 유효하지 않습니다."
            )

    boolean_fields = {
        "source_loaded": result.source_loaded,
        "source_valid": result.source_valid,
        "policy_checks_passed": (
            result.policy_checks_passed
        ),
        "price_checks_passed": (
            result.price_checks_passed
        ),
        "position_checks_passed": (
            result.position_checks_passed
        ),
        "total_checks_passed": (
            result.total_checks_passed
        ),
        "all_checks_passed": (
            result.all_checks_passed
        ),
        "portfolio_updated": (
            result.portfolio_updated
        ),
        "execution_blocked": (
            result.execution_blocked
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
    }

    for field_name, value in boolean_fields.items():
        if not isinstance(
            value,
            bool,
        ):
            raise RuntimeError(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    if not result.execution_blocked:
        raise RuntimeError(
            "Execution이 차단되지 않았습니다."
        )

    if result.broker_api_called:
        raise RuntimeError(
            "실제 Broker API가 호출되었습니다."
        )

    if result.broker_order_created:
        raise RuntimeError(
            "실제 Broker Order가 생성되었습니다."
        )

    if result.live_order_created:
        raise RuntimeError(
            "Live Order가 생성되었습니다."
        )

    if result.live_execution_authorized:
        raise RuntimeError(
            "Live Execution이 허용되었습니다."
        )

    expected_equity = round_money(
        result.cash_balance
        + result.updated_total_market_value
    )

    assert_close(
        actual=result.updated_total_equity,
        expected=expected_equity,
        message=(
            "Updated Equity가 Cash + Market Value와 "
            "일치하지 않습니다."
        ),
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


def validate_normal_valuation_scenario(
    portfolio: PaperPortfolioState,
) -> PaperPortfolioValuationResult:
    """
    가격 상승 정상 평가 시나리오입니다.
    """

    result = run_paper_portfolio_valuation(
        portfolio_state=portfolio,
        latest_prices={
            "AAPL": 250.0,
        },
        valuation_policy=(
            PaperPortfolioValuationPolicy()
        ),
        initial_cash=INITIAL_CASH,
    )

    validate_result_common(
        result
    )

    if result.valuation_status != "VALUED":
        raise RuntimeError(
            "정상 평가 Status가 VALUED가 아닙니다."
        )

    if not result.source_loaded:
        raise RuntimeError(
            "정상 평가 Source Loaded가 False입니다."
        )

    if not result.source_valid:
        raise RuntimeError(
            "정상 평가 Source Valid가 False입니다."
        )

    if not result.policy_checks_passed:
        raise RuntimeError(
            "정상 평가 Policy Checks가 실패했습니다."
        )

    if not result.price_checks_passed:
        raise RuntimeError(
            "정상 평가 Price Checks가 실패했습니다."
        )

    if not result.position_checks_passed:
        raise RuntimeError(
            "정상 평가 Position Checks가 실패했습니다."
        )

    if not result.total_checks_passed:
        raise RuntimeError(
            "정상 평가 Total Checks가 실패했습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "정상 평가 All Checks가 실패했습니다."
        )

    if not result.portfolio_updated:
        raise RuntimeError(
            "정상 평가 Portfolio가 업데이트되지 않았습니다."
        )

    if result.long_position_count != 1:
        raise RuntimeError(
            "정상 평가 Long Position Count가 1이 아닙니다."
        )

    if result.valued_position_count != 1:
        raise RuntimeError(
            "정상 평가 Valued Position Count가 1이 아닙니다."
        )

    if result.missing_price_count != 0:
        raise RuntimeError(
            "정상 평가에서 Missing Price가 존재합니다."
        )

    if result.invalid_price_count != 0:
        raise RuntimeError(
            "정상 평가에서 Invalid Price가 존재합니다."
        )

    assert_close(
        actual=result.updated_total_market_value,
        expected=2_500.0,
        message="정상 평가 Market Value가 다릅니다.",
    )

    assert_close(
        actual=result.updated_total_unrealized_pnl,
        expected=500.0,
        message="정상 평가 Unrealized PnL이 다릅니다.",
    )

    assert_close(
        actual=result.updated_total_equity,
        expected=10_500.0,
        message="정상 평가 Total Equity가 다릅니다.",
    )

    assert_close(
        actual=result.total_profit_loss,
        expected=500.0,
        message="정상 평가 Total P/L이 다릅니다.",
    )

    assert_close(
        actual=result.total_return_percent,
        expected=5.0,
        tolerance=0.0001,
        message="정상 평가 Total Return이 다릅니다.",
    )

    assert_close(
        actual=result.cash_weight_percent,
        expected=76.1905,
        tolerance=0.001,
        message="정상 평가 Cash Weight가 다릅니다.",
    )

    assert_close(
        actual=result.invested_weight_percent,
        expected=23.8095,
        tolerance=0.001,
        message="정상 평가 Invested Weight가 다릅니다.",
    )

    aapl = result.position_valuations[
        "AAPL"
    ]

    assert_close(
        actual=aapl.portfolio_weight_percent,
        expected=23.8095,
        tolerance=0.001,
        message="AAPL Portfolio Weight가 다릅니다.",
    )

    return result


def validate_price_decline_scenario(
    portfolio: PaperPortfolioState,
) -> PaperPortfolioValuationResult:
    """
    가격 하락 시 미실현 손실 계산을 검사합니다.
    """

    result = run_paper_portfolio_valuation(
        portfolio_state=portfolio,
        latest_prices={
            "AAPL": 150.0,
        },
    )

    validate_result_common(
        result
    )

    if result.valuation_status != "VALUED":
        raise RuntimeError(
            "가격 하락 평가 Status가 VALUED가 아닙니다."
        )

    assert_close(
        actual=result.updated_total_market_value,
        expected=1_500.0,
        message="가격 하락 Market Value가 다릅니다.",
    )

    assert_close(
        actual=result.updated_total_unrealized_pnl,
        expected=-500.0,
        message="가격 하락 Unrealized PnL이 다릅니다.",
    )

    assert_close(
        actual=result.updated_total_equity,
        expected=9_500.0,
        message="가격 하락 Total Equity가 다릅니다.",
    )

    assert_close(
        actual=result.total_profit_loss,
        expected=-500.0,
        message="가격 하락 Total P/L이 다릅니다.",
    )

    assert_close(
        actual=result.total_return_percent,
        expected=-5.0,
        tolerance=0.0001,
        message="가격 하락 Total Return이 다릅니다.",
    )

    return result


def validate_missing_price_blocked_scenario(
    portfolio: PaperPortfolioState,
) -> PaperPortfolioValuationResult:
    """
    필수 가격 누락 시 BLOCKED 결과를 검사합니다.
    """

    with patch(
        "backtest.paper_portfolio_valuation."
        "fetch_latest_market_price",
        side_effect=RuntimeError(
            "테스트용 Market Data 실패"
        ),
    ):
        result = run_paper_portfolio_valuation(
            portfolio_state=portfolio,
            latest_prices={},
            valuation_policy=(
                PaperPortfolioValuationPolicy(
                    require_all_prices=True,
                    allow_position_price_fallback=False,
                )
            ),
        )

    validate_result_common(
        result
    )

    if result.valuation_status != "BLOCKED":
        raise RuntimeError(
            "가격 누락 Status가 BLOCKED가 아닙니다."
        )

    if result.price_checks_passed:
        raise RuntimeError(
            "가격 누락에서 Price Checks가 True입니다."
        )

    if result.portfolio_updated:
        raise RuntimeError(
            "가격 누락에서 Portfolio가 업데이트되었습니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "가격 누락에서 All Checks가 True입니다."
        )

    if result.missing_price_count != 1:
        raise RuntimeError(
            "가격 누락 Count가 1이 아닙니다."
        )

    if (
        result.position_valuations["AAPL"]
        .valuation_status
        != "PRICE_MISSING"
    ):
        raise RuntimeError(
            "AAPL Status가 PRICE_MISSING이 아닙니다."
        )

    return result


def validate_invalid_price_blocked_scenario(
    portfolio: PaperPortfolioState,
) -> PaperPortfolioValuationResult:
    """
    0 가격 입력 시 BLOCKED 결과를 검사합니다.
    """

    result = run_paper_portfolio_valuation(
        portfolio_state=portfolio,
        latest_prices={
            "AAPL": 0.0,
        },
        valuation_policy=(
            PaperPortfolioValuationPolicy(
                require_all_prices=True,
                allow_zero_position_price=False,
            )
        ),
    )

    validate_result_common(
        result
    )

    if result.valuation_status != "BLOCKED":
        raise RuntimeError(
            "0 가격 Status가 BLOCKED가 아닙니다."
        )

    if result.price_checks_passed:
        raise RuntimeError(
            "0 가격에서 Price Checks가 True입니다."
        )

    if result.portfolio_updated:
        raise RuntimeError(
            "0 가격에서 Portfolio가 업데이트되었습니다."
        )

    if result.all_checks_passed:
        raise RuntimeError(
            "0 가격에서 All Checks가 True입니다."
        )

    if result.invalid_price_count != 1:
        raise RuntimeError(
            "Invalid Price Count가 1이 아닙니다."
        )

    if (
        result.position_valuations["AAPL"]
        .valuation_status
        != "INVALID_PRICE"
    ):
        raise RuntimeError(
            "AAPL Status가 INVALID_PRICE가 아닙니다."
        )

    return result


def validate_partial_valuation_scenario() -> (
    PaperPortfolioValuationResult
):
    """
    두 종목 중 한 종목만 평가되는 PARTIAL 시나리오입니다.
    """

    portfolio = create_test_portfolio(
        symbol="AAPL",
        cash_balance=6_500.0,
        shares=10,
        average_price=200.0,
        latest_price=200.0,
    )

    add_second_position(
        portfolio=portfolio,
        symbol="MSFT",
        shares=5,
        average_price=300.0,
        latest_price=300.0,
    )

    with patch(
        "backtest.paper_portfolio_valuation."
        "fetch_latest_market_price",
        side_effect=RuntimeError(
            "테스트용 MSFT 가격 조회 실패"
        ),
    ):
        result = run_paper_portfolio_valuation(
            portfolio_state=portfolio,
            latest_prices={
                "AAPL": 250.0,
            },
            valuation_policy=(
                PaperPortfolioValuationPolicy(
                    require_all_prices=False,
                    allow_position_price_fallback=False,
                )
            ),
        )

    validate_result_common(
        result
    )

    if result.valuation_status != "PARTIAL":
        raise RuntimeError(
            "일부 가격 평가 Status가 PARTIAL이 아닙니다."
        )

    if not result.price_checks_passed:
        raise RuntimeError(
            "Partial 정책에서 Price Checks가 False입니다."
        )

    if not result.portfolio_updated:
        raise RuntimeError(
            "Partial 평가에서 Portfolio가 "
            "업데이트되지 않았습니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "Partial 평가에서 All Checks가 False입니다."
        )

    if result.long_position_count != 2:
        raise RuntimeError(
            "Partial 평가 Long Position Count가 2가 아닙니다."
        )

    if result.valued_position_count != 1:
        raise RuntimeError(
            "Partial 평가 Valued Position Count가 1이 아닙니다."
        )

    if result.missing_price_count != 1:
        raise RuntimeError(
            "Partial 평가 Missing Price Count가 1이 아닙니다."
        )

    if (
        result.position_valuations["AAPL"]
        .valuation_status
        != "VALUED"
    ):
        raise RuntimeError(
            "Partial 평가에서 AAPL이 VALUED가 아닙니다."
        )

    if (
        result.position_valuations["MSFT"]
        .valuation_status
        != "PRICE_MISSING"
    ):
        raise RuntimeError(
            "Partial 평가에서 MSFT가 "
            "PRICE_MISSING이 아닙니다."
        )

    assert_close(
        actual=result.updated_total_market_value,
        expected=4_000.0,
        message=(
            "Partial 평가 Total Market Value가 "
            "일치하지 않습니다."
        ),
    )

    assert_close(
        actual=result.updated_total_equity,
        expected=10_500.0,
        message=(
            "Partial 평가 Total Equity가 "
            "일치하지 않습니다."
        ),
    )

    return result


def validate_flat_portfolio_scenario() -> (
    PaperPortfolioValuationResult
):
    """
    Long Position이 없는 NO_POSITIONS 결과를 검사합니다.
    """

    portfolio = create_empty_portfolio(
        initial_cash=10_000.0
    )

    portfolio.cash_balance = 10_250.0

    portfolio.positions[
        "AAPL"
    ] = PaperPosition(
        symbol="AAPL",
        state="FLAT",
        shares=0,
        average_price=0.0,
        cost_basis=0.0,
        latest_price=125.0,
        market_value=0.0,
        unrealized_pnl=0.0,
        unrealized_pnl_percent=0.0,
        realized_pnl=250.0,
    )

    recalculate_portfolio_totals(
        portfolio
    )

    result = run_paper_portfolio_valuation(
        portfolio_state=portfolio,
        latest_prices={},
    )

    validate_result_common(
        result
    )

    if result.valuation_status != "NO_POSITIONS":
        raise RuntimeError(
            "FLAT Portfolio Status가 "
            "NO_POSITIONS가 아닙니다."
        )

    if result.long_position_count != 0:
        raise RuntimeError(
            "FLAT Portfolio Long Count가 0이 아닙니다."
        )

    if result.flat_position_count != 1:
        raise RuntimeError(
            "FLAT Portfolio Flat Count가 1이 아닙니다."
        )

    if not result.all_checks_passed:
        raise RuntimeError(
            "FLAT Portfolio All Checks가 False입니다."
        )

    if not result.portfolio_updated:
        raise RuntimeError(
            "FLAT Portfolio가 업데이트되지 않았습니다."
        )

    assert_close(
        actual=result.updated_total_market_value,
        expected=0.0,
        message="FLAT Portfolio Market Value가 0이 아닙니다.",
    )

    assert_close(
        actual=result.updated_total_equity,
        expected=10_250.0,
        message="FLAT Portfolio Equity가 다릅니다.",
    )

    assert_close(
        actual=result.cash_weight_percent,
        expected=100.0,
        tolerance=0.0001,
        message="FLAT Portfolio Cash Weight가 다릅니다.",
    )

    assert_close(
        actual=result.invested_weight_percent,
        expected=0.0,
        tolerance=0.0001,
        message="FLAT Portfolio Invested Weight가 다릅니다.",
    )

    return result


def validate_update_helpers(
    portfolio: PaperPortfolioState,
    policy: PaperPortfolioValuationPolicy,
) -> None:
    """
    Position 반영 및 Portfolio 합계 Helper를 검사합니다.
    """

    valuation = calculate_position_valuation(
        position=portfolio.positions[
            "AAPL"
        ],
        latest_price=275.0,
        price_source="PROVIDED",
        price_source_label="테스트 제공 가격",
        policy=policy,
    )

    update_portfolio_position(
        portfolio=portfolio,
        valuation=valuation,
    )

    position = portfolio.positions[
        "AAPL"
    ]

    assert_close(
        actual=position.latest_price,
        expected=275.0,
        tolerance=0.0001,
        message="Updated Position Price가 다릅니다.",
    )

    assert_close(
        actual=position.market_value,
        expected=2_750.0,
        message="Updated Position Market Value가 다릅니다.",
    )

    assert_close(
        actual=position.unrealized_pnl,
        expected=750.0,
        message="Updated Position Unrealized PnL이 다릅니다.",
    )

    recalculate_valued_portfolio_totals(
        portfolio
    )

    assert_close(
        actual=portfolio.total_market_value,
        expected=2_750.0,
        message="Recalculated Market Value가 다릅니다.",
    )

    assert_close(
        actual=portfolio.total_unrealized_pnl,
        expected=750.0,
        message="Recalculated Unrealized PnL이 다릅니다.",
    )

    assert_close(
        actual=portfolio.total_equity,
        expected=10_750.0,
        message="Recalculated Total Equity가 다릅니다.",
    )


def validate_save_and_load(
    result: PaperPortfolioValuationResult,
) -> tuple[
    Path,
    Path,
    Path,
    Path,
]:
    """
    평가 결과 저장 및 다시 불러오기를 검사합니다.
    """

    (
        report_path,
        latest_path,
        snapshot_path,
        updated_state_path,
    ) = save_paper_portfolio_valuation(
        result
    )

    paths = {
        "Report": report_path,
        "Latest": latest_path,
        "Snapshot": snapshot_path,
        "Updated State": updated_state_path,
    }

    for name, file_path in paths.items():
        if not file_path.exists():
            raise RuntimeError(
                f"{name} 파일이 생성되지 않았습니다: "
                f"{file_path}"
            )

        if file_path.stat().st_size <= 0:
            raise RuntimeError(
                f"{name} 파일이 비어 있습니다: "
                f"{file_path}"
            )

    report_payload = read_json_file(
        report_path
    )

    latest_payload = read_json_file(
        latest_path
    )

    snapshot_payload = read_json_file(
        snapshot_path
    )

    updated_state_payload = read_json_file(
        updated_state_path
    )

    if report_payload != latest_payload:
        raise RuntimeError(
            "Report와 Latest JSON 내용이 다릅니다."
        )

    if report_payload != result.to_dict():
        raise RuntimeError(
            "저장된 Report JSON이 Result와 다릅니다."
        )

    if (
        snapshot_payload.get(
            "valuation_id"
        )
        != result.valuation_id
    ):
        raise RuntimeError(
            "Snapshot Valuation ID가 다릅니다."
        )

    if (
        snapshot_payload.get(
            "portfolio_id"
        )
        != result.portfolio_id
    ):
        raise RuntimeError(
            "Snapshot Portfolio ID가 다릅니다."
        )

    if (
        updated_state_payload
        != result.updated_portfolio_state.to_dict()
    ):
        raise RuntimeError(
            "Updated State JSON이 Portfolio State와 다릅니다."
        )

    loaded_payload = load_latest_valuation_result()

    if loaded_payload != latest_payload:
        raise RuntimeError(
            "load_latest_valuation_result 결과가 다릅니다."
        )

    loaded_portfolio = (
        load_valuation_portfolio_state(
            file_path=latest_path
        )
    )

    if (
        loaded_portfolio.to_dict()
        != result.updated_portfolio_state.to_dict()
    ):
        raise RuntimeError(
            "load_valuation_portfolio_state 결과가 다릅니다."
        )

    if result.report_path != str(
        report_path
    ):
        raise RuntimeError(
            "Result Report Path가 실제 경로와 다릅니다."
        )

    if result.latest_path != str(
        latest_path
    ):
        raise RuntimeError(
            "Result Latest Path가 실제 경로와 다릅니다."
        )

    if result.snapshot_path != str(
        snapshot_path
    ):
        raise RuntimeError(
            "Result Snapshot Path가 실제 경로와 다릅니다."
        )

    if result.updated_state_path != str(
        updated_state_path
    ):
        raise RuntimeError(
            "Result Updated State Path가 실제 경로와 다릅니다."
        )

    return (
        report_path,
        latest_path,
        snapshot_path,
        updated_state_path,
    )


def print_scenario_summary(
    normal_result: PaperPortfolioValuationResult,
    decline_result: PaperPortfolioValuationResult,
    missing_result: PaperPortfolioValuationResult,
    invalid_result: PaperPortfolioValuationResult,
    partial_result: PaperPortfolioValuationResult,
    flat_result: PaperPortfolioValuationResult,
    report_path: Path,
    latest_path: Path,
    snapshot_path: Path,
    updated_state_path: Path,
) -> None:
    """
    주요 테스트 결과를 출력합니다.
    """

    print()
    print("=" * LINE_LENGTH)
    print(
        "V10.0 PAPER PORTFOLIO VALUATION "
        "TEST RESULT"
    )
    print("=" * LINE_LENGTH)

    print("NORMAL PRICE INCREASE")
    print("-" * LINE_LENGTH)

    print(
        f"Status                         : "
        f"{normal_result.valuation_status}"
    )

    print(
        f"Market value                   : "
        f"${normal_result.updated_total_market_value:,.2f}"
    )

    print(
        f"Unrealized PnL                 : "
        f"${normal_result.updated_total_unrealized_pnl:,.2f}"
    )

    print(
        f"Total equity                   : "
        f"${normal_result.updated_total_equity:,.2f}"
    )

    print(
        f"Total return                   : "
        f"{normal_result.total_return_percent:.4f}%"
    )

    print()
    print("PRICE DECLINE")
    print("-" * LINE_LENGTH)

    print(
        f"Status                         : "
        f"{decline_result.valuation_status}"
    )

    print(
        f"Market value                   : "
        f"${decline_result.updated_total_market_value:,.2f}"
    )

    print(
        f"Unrealized PnL                 : "
        f"${decline_result.updated_total_unrealized_pnl:,.2f}"
    )

    print(
        f"Total return                   : "
        f"{decline_result.total_return_percent:.4f}%"
    )

    print()
    print("PRICE SAFETY SCENARIOS")
    print("-" * LINE_LENGTH)

    print(
        f"Missing price status           : "
        f"{missing_result.valuation_status}"
    )

    print(
        f"Invalid price status           : "
        f"{invalid_result.valuation_status}"
    )

    print(
        f"Partial valuation status       : "
        f"{partial_result.valuation_status}"
    )

    print(
        f"No positions status            : "
        f"{flat_result.valuation_status}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * LINE_LENGTH)

    print(
        f"Execution blocked              : "
        f"{normal_result.execution_blocked}"
    )

    print(
        f"Broker API called              : "
        f"{normal_result.broker_api_called}"
    )

    print(
        f"Broker order created           : "
        f"{normal_result.broker_order_created}"
    )

    print(
        f"Live order created             : "
        f"{normal_result.live_order_created}"
    )

    print(
        f"Live execution authorized      : "
        f"{normal_result.live_execution_authorized}"
    )

    print()
    print("FILES")
    print("-" * LINE_LENGTH)

    print(
        f"Output directory               : "
        f"{PAPER_VALUATION_OUTPUT_DIRECTORY}"
    )

    print(
        f"Report file                    : "
        f"{report_path}"
    )

    print(
        f"Latest file                    : "
        f"{latest_path}"
    )

    print(
        f"Snapshot file                  : "
        f"{snapshot_path}"
    )

    print(
        f"Updated state file             : "
        f"{updated_state_path}"
    )

    print("=" * LINE_LENGTH)


def print_validation_checks(
    normal_result: PaperPortfolioValuationResult,
    decline_result: PaperPortfolioValuationResult,
    missing_result: PaperPortfolioValuationResult,
    invalid_result: PaperPortfolioValuationResult,
    partial_result: PaperPortfolioValuationResult,
    flat_result: PaperPortfolioValuationResult,
    report_path: Path,
    latest_path: Path,
    snapshot_path: Path,
    updated_state_path: Path,
) -> None:
    """
    최종 검증 항목을 출력합니다.
    """

    checks = {
        "Version is V10.0": (
            normal_result.version == "V10.0"
        ),
        "Normal status is VALUED": (
            normal_result.valuation_status
            == "VALUED"
        ),
        "Normal price checks passed": (
            normal_result.price_checks_passed
        ),
        "Normal portfolio updated": (
            normal_result.portfolio_updated
        ),
        "Normal all checks passed": (
            normal_result.all_checks_passed
        ),
        "Normal market value matches": (
            abs(
                normal_result.updated_total_market_value
                - 2_500.0
            )
            <= 0.01
        ),
        "Normal unrealized PnL matches": (
            abs(
                normal_result.updated_total_unrealized_pnl
                - 500.0
            )
            <= 0.01
        ),
        "Normal equity matches": (
            abs(
                normal_result.updated_total_equity
                - 10_500.0
            )
            <= 0.01
        ),
        "Decline status is VALUED": (
            decline_result.valuation_status
            == "VALUED"
        ),
        "Decline unrealized PnL matches": (
            abs(
                decline_result.updated_total_unrealized_pnl
                + 500.0
            )
            <= 0.01
        ),
        "Missing price status is BLOCKED": (
            missing_result.valuation_status
            == "BLOCKED"
        ),
        "Missing price count is one": (
            missing_result.missing_price_count
            == 1
        ),
        "Missing price did not update": (
            not missing_result.portfolio_updated
        ),
        "Invalid price status is BLOCKED": (
            invalid_result.valuation_status
            == "BLOCKED"
        ),
        "Invalid price count is one": (
            invalid_result.invalid_price_count
            == 1
        ),
        "Invalid price did not update": (
            not invalid_result.portfolio_updated
        ),
        "Partial status is PARTIAL": (
            partial_result.valuation_status
            == "PARTIAL"
        ),
        "Partial valued count is one": (
            partial_result.valued_position_count
            == 1
        ),
        "Partial missing count is one": (
            partial_result.missing_price_count
            == 1
        ),
        "Partial portfolio updated": (
            partial_result.portfolio_updated
        ),
        "Partial all checks passed": (
            partial_result.all_checks_passed
        ),
        "Flat status is NO_POSITIONS": (
            flat_result.valuation_status
            == "NO_POSITIONS"
        ),
        "Flat long count is zero": (
            flat_result.long_position_count
            == 0
        ),
        "Flat all checks passed": (
            flat_result.all_checks_passed
        ),
        "Execution remains blocked": (
            normal_result.execution_blocked
        ),
        "Broker API was not called": (
            not normal_result.broker_api_called
        ),
        "Broker order was not created": (
            not normal_result.broker_order_created
        ),
        "Live order was not created": (
            not normal_result.live_order_created
        ),
        "Live execution not authorized": (
            not normal_result.live_execution_authorized
        ),
        "Report file exists": (
            report_path.exists()
        ),
        "Latest file exists": (
            latest_path.exists()
        ),
        "Snapshot file exists": (
            snapshot_path.exists()
        ),
        "Updated state file exists": (
            updated_state_path.exists()
        ),
        "Reasons exist": bool(
            normal_result.reasons
        ),
        "Warnings exist": bool(
            normal_result.warnings
        ),
        "Next actions exist": bool(
            normal_result.next_actions
        ),
    }

    print()
    print("=" * LINE_LENGTH)
    print("VALIDATION CHECKS")
    print("=" * LINE_LENGTH)

    for name, value in checks.items():
        print_check(
            name=name,
            value=value,
        )

    print("=" * LINE_LENGTH)

    failed_checks = [
        name
        for name, value in checks.items()
        if not value
    ]

    if failed_checks:
        raise RuntimeError(
            "다음 V10.0 검증 항목이 실패했습니다: "
            f"{failed_checks}"
        )


def main() -> None:
    """
    V10.0 Paper Portfolio Valuation 통합 테스트입니다.

    검증 항목:

    1. Policy 구조 및 불변성
    2. 잘못된 Policy 차단
    3. 가격 검증
    4. Market DataFrame 최신 Close 추출
    5. 제공 가격 정규화
    6. 가격 Resolve 우선순위
    7. Position Valuation 계산
    8. 가격 상승 평가
    9. 가격 하락 평가
    10. 가격 누락 차단
    11. 0 가격 차단
    12. Partial Valuation
    13. FLAT Portfolio 평가
    14. Portfolio Weight 계산
    15. JSON 저장 및 재로딩
    16. 실제 Broker 및 Live Execution 차단
    """

    print_header()

    try:
        policy = validate_policy_structure()

        validate_policy_immutable(
            policy
        )

        validate_invalid_policies()

        validate_utility_functions()

        validate_market_price_rules(
            policy
        )

        validate_dataframe_price_extraction()

        validate_price_normalization()

        base_portfolio = create_test_portfolio()

        validate_price_resolution(
            portfolio=base_portfolio,
            policy=policy,
        )

        validate_position_valuation_calculation(
            portfolio=base_portfolio,
            policy=policy,
        )

        validate_flat_position_calculation(
            policy=policy
        )

        validate_missing_price_calculation(
            portfolio=base_portfolio,
            policy=policy,
        )

        validate_invalid_price_calculation(
            portfolio=base_portfolio,
            policy=policy,
        )

        validate_weight_calculation()

        helper_portfolio = create_test_portfolio()

        validate_update_helpers(
            portfolio=helper_portfolio,
            policy=policy,
        )

        normal_portfolio = create_test_portfolio()

        normal_result = (
            validate_normal_valuation_scenario(
                portfolio=normal_portfolio
            )
        )

        decline_portfolio = create_test_portfolio()

        decline_result = (
            validate_price_decline_scenario(
                portfolio=decline_portfolio
            )
        )

        missing_portfolio = create_test_portfolio()

        missing_result = (
            validate_missing_price_blocked_scenario(
                portfolio=missing_portfolio
            )
        )

        invalid_portfolio = create_test_portfolio()

        invalid_result = (
            validate_invalid_price_blocked_scenario(
                portfolio=invalid_portfolio
            )
        )

        partial_result = (
            validate_partial_valuation_scenario()
        )

        flat_result = (
            validate_flat_portfolio_scenario()
        )

        (
            report_path,
            latest_path,
            snapshot_path,
            updated_state_path,
        ) = validate_save_and_load(
            normal_result
        )

        print_scenario_summary(
            normal_result=normal_result,
            decline_result=decline_result,
            missing_result=missing_result,
            invalid_result=invalid_result,
            partial_result=partial_result,
            flat_result=flat_result,
            report_path=report_path,
            latest_path=latest_path,
            snapshot_path=snapshot_path,
            updated_state_path=updated_state_path,
        )

        print_validation_checks(
            normal_result=normal_result,
            decline_result=decline_result,
            missing_result=missing_result,
            invalid_result=invalid_result,
            partial_result=partial_result,
            flat_result=flat_result,
            report_path=report_path,
            latest_path=latest_path,
            snapshot_path=snapshot_path,
            updated_state_path=updated_state_path,
        )

        print()
        print(
            "V10.0 paper portfolio valuation "
            "test completed successfully."
        )

        print(
            "가격 상승과 가격 하락에 따른 시장가치 및 "
            "미실현 손익이 정상 계산되었습니다."
        )

        print(
            "가격 누락과 유효하지 않은 가격은 "
            "정상적으로 차단되었습니다."
        )

        print(
            "일부 가격만 제공된 경우 PARTIAL 평가가 "
            "정상 처리되었습니다."
        )

        print(
            "Long Position이 없는 Portfolio는 "
            "NO_POSITIONS로 정상 처리되었습니다."
        )

        print(
            "평가 Report, Latest, Snapshot 및 "
            "Portfolio State가 정상 저장되고 재로딩되었습니다."
        )

        print(
            "실제 Broker API, Broker Order, Live Order 및 "
            "Live Execution은 모두 차단되었습니다."
        )

        print(
            "주의: 이 테스트는 연구용 Paper Trading "
            "가상 평가이며 실제 증권 거래가 아닙니다."
        )

    except KeyboardInterrupt:
        print()
        print("=" * LINE_LENGTH)
        print("V10.0 TEST CANCELLED")
        print("=" * LINE_LENGTH)

        print(
            "사용자가 V10.0 Paper Portfolio Valuation "
            "테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * LINE_LENGTH)
        print(
            "V10.0 PAPER PORTFOLIO VALUATION ERROR"
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