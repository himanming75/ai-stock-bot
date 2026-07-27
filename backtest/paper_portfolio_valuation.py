import json
import math
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from backtest.paper_portfolio_manager import (
    PaperPortfolioState,
    PaperPosition,
    copy_portfolio_state,
    load_latest_portfolio_state,
    portfolio_from_dict,
    validate_portfolio_state,
)
from data.market import get_history


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PAPER_VALUATION_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "trading_engine"
    / "paper_portfolio_valuation"
)


VALID_VALUATION_STATUSES = {
    "VALUED",
    "PARTIAL",
    "NO_POSITIONS",
    "BLOCKED",
    "FAILED",
}


VALID_POSITION_VALUATION_STATUSES = {
    "VALUED",
    "FLAT",
    "PRICE_MISSING",
    "INVALID_PRICE",
    "BLOCKED",
}


VALID_PRICE_SOURCES = {
    "PROVIDED",
    "MARKET_DATA",
    "POSITION_PRICE",
    "NOT_REQUIRED",
    "UNAVAILABLE",
}


@dataclass(frozen=True)
class PaperPortfolioValuationPolicy:
    """
    V10.0 Paper Portfolio Valuation 정책입니다.

    이 정책은 연구용 Paper Portfolio 평가만 수행합니다.
    실제 계좌나 실제 주문에는 연결되지 않습니다.
    """

    require_all_prices: bool = True
    allow_position_price_fallback: bool = False
    allow_zero_position_price: bool = False

    minimum_valid_price: float = 0.01
    maximum_valid_price: float = 1_000_000.0

    price_period: str = "5d"
    price_interval: str = "1d"

    cash_weight_warning_percent: float = 80.0
    invested_weight_warning_percent: float = 95.0

    paper_only: bool = True
    live_execution_disabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperPositionValuation:
    """
    종목별 Paper Position 평가 결과입니다.
    """

    symbol: str

    valuation_status: str
    valuation_status_label: str

    position_state: str
    shares: int

    average_price: float
    cost_basis: float

    previous_price: float
    latest_price: float
    price_change: float
    price_change_percent: float

    price_source: str
    price_source_label: str

    previous_market_value: float
    market_value: float
    market_value_change: float

    unrealized_pnl: float
    unrealized_pnl_percent: float
    realized_pnl: float

    portfolio_weight_percent: float

    price_loaded: bool
    price_valid: bool
    valuation_calculated: bool
    checks_passed: bool

    reasons: list[str] = field(
        default_factory=list
    )

    warnings: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperPortfolioValuationResult:
    """
    V10.0 Paper Portfolio Valuation 전체 결과입니다.
    """

    version: str
    created_at: str

    valuation_id: str
    portfolio_id: str

    valuation_status: str
    valuation_status_label: str

    source_portfolio_file: str | None

    initial_cash: float
    cash_balance: float

    previous_total_market_value: float
    updated_total_market_value: float
    total_market_value_change: float

    previous_total_unrealized_pnl: float
    updated_total_unrealized_pnl: float
    total_unrealized_pnl_change: float

    total_realized_pnl: float
    total_commission: float

    previous_total_equity: float
    updated_total_equity: float
    total_equity_change: float
    total_equity_change_percent: float

    total_profit_loss: float
    total_return_percent: float

    cash_weight_percent: float
    invested_weight_percent: float

    position_count: int
    long_position_count: int
    flat_position_count: int

    valued_position_count: int
    missing_price_count: int
    invalid_price_count: int

    source_loaded: bool
    source_valid: bool

    policy_checks_passed: bool
    price_checks_passed: bool
    position_checks_passed: bool
    total_checks_passed: bool
    all_checks_passed: bool

    portfolio_updated: bool

    execution_blocked: bool
    broker_api_called: bool
    broker_order_created: bool
    live_order_created: bool
    live_execution_authorized: bool

    valuation_policy: PaperPortfolioValuationPolicy
    position_valuations: dict[
        str,
        PaperPositionValuation,
    ]

    updated_portfolio_state: PaperPortfolioState

    reasons: list[str]
    warnings: list[str]
    next_actions: list[str]

    report_path: str | None = None
    latest_path: str | None = None
    snapshot_path: str | None = None
    updated_state_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)

        payload["valuation_policy"] = (
            self.valuation_policy.to_dict()
        )

        payload["position_valuations"] = {
            symbol: valuation.to_dict()
            for symbol, valuation
            in self.position_valuations.items()
        }

        payload["updated_portfolio_state"] = (
            self.updated_portfolio_state.to_dict()
        )

        return payload


def normalize_symbol(
    symbol: str,
) -> str:
    """
    Symbol을 대문자로 정규화합니다.
    """

    normalized = str(
        symbol
    ).strip().upper()

    if not normalized:
        raise ValueError(
            "Symbol이 비어 있습니다."
        )

    return normalized


def is_valid_number(
    value: Any,
) -> bool:
    """
    유한한 숫자인지 검사합니다.
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


def round_money(
    value: float,
) -> float:
    """
    금액을 소수점 둘째 자리로 반올림합니다.
    """

    return round(
        float(value),
        2,
    )


def round_price(
    value: float,
) -> float:
    """
    가격을 소수점 넷째 자리로 반올림합니다.
    """

    return round(
        float(value),
        4,
    )


def round_percent(
    value: float,
) -> float:
    """
    비율을 소수점 넷째 자리로 반올림합니다.
    """

    return round(
        float(value),
        4,
    )


def write_json_file(
    file_path: Path,
    payload: dict[str, Any],
) -> None:
    """
    JSON 파일을 임시 파일 방식으로 저장합니다.
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


def validate_valuation_policy(
    policy: PaperPortfolioValuationPolicy,
) -> tuple[
    bool,
    list[str],
]:
    """
    V10.0 Valuation Policy를 검사합니다.
    """

    errors: list[str] = []

    if not isinstance(
        policy,
        PaperPortfolioValuationPolicy,
    ):
        return (
            False,
            [
                (
                    "Policy가 "
                    "PaperPortfolioValuationPolicy "
                    "형식이 아닙니다."
                )
            ],
        )

    boolean_fields = {
        "require_all_prices": (
            policy.require_all_prices
        ),
        "allow_position_price_fallback": (
            policy.allow_position_price_fallback
        ),
        "allow_zero_position_price": (
            policy.allow_zero_position_price
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
            errors.append(
                f"{field_name}가 bool 형식이 아닙니다."
            )

    numeric_fields = {
        "minimum_valid_price": (
            policy.minimum_valid_price
        ),
        "maximum_valid_price": (
            policy.maximum_valid_price
        ),
        "cash_weight_warning_percent": (
            policy.cash_weight_warning_percent
        ),
        "invested_weight_warning_percent": (
            policy.invested_weight_warning_percent
        ),
    }

    for field_name, value in numeric_fields.items():
        if not is_valid_number(
            value
        ):
            errors.append(
                f"{field_name}가 유효한 숫자가 아닙니다."
            )

    if (
        is_valid_number(
            policy.minimum_valid_price
        )
        and policy.minimum_valid_price <= 0
    ):
        errors.append(
            "Minimum Valid Price는 0보다 커야 합니다."
        )

    if (
        is_valid_number(
            policy.maximum_valid_price
        )
        and policy.maximum_valid_price <= 0
    ):
        errors.append(
            "Maximum Valid Price는 0보다 커야 합니다."
        )

    if (
        is_valid_number(
            policy.minimum_valid_price
        )
        and is_valid_number(
            policy.maximum_valid_price
        )
        and policy.minimum_valid_price
        >= policy.maximum_valid_price
    ):
        errors.append(
            "Minimum Valid Price는 Maximum Valid Price보다 "
            "작아야 합니다."
        )

    if (
        is_valid_number(
            policy.cash_weight_warning_percent
        )
        and not (
            0
            <= policy.cash_weight_warning_percent
            <= 100
        )
    ):
        errors.append(
            "Cash Weight Warning Percent는 "
            "0부터 100 사이여야 합니다."
        )

    if (
        is_valid_number(
            policy.invested_weight_warning_percent
        )
        and not (
            0
            <= policy.invested_weight_warning_percent
            <= 100
        )
    ):
        errors.append(
            "Invested Weight Warning Percent는 "
            "0부터 100 사이여야 합니다."
        )

    if not isinstance(
        policy.price_period,
        str,
    ):
        errors.append(
            "Price Period가 문자열이 아닙니다."
        )

    elif not policy.price_period.strip():
        errors.append(
            "Price Period가 비어 있습니다."
        )

    if not isinstance(
        policy.price_interval,
        str,
    ):
        errors.append(
            "Price Interval이 문자열이 아닙니다."
        )

    elif not policy.price_interval.strip():
        errors.append(
            "Price Interval이 비어 있습니다."
        )

    if not policy.paper_only:
        errors.append(
            "V10.0에서는 Paper Only가 True여야 합니다."
        )

    if not policy.live_execution_disabled:
        errors.append(
            "V10.0에서는 Live Execution Disabled가 "
            "True여야 합니다."
        )

    return (
        not errors,
        errors,
    )


def validate_market_price(
    price: Any,
    policy: PaperPortfolioValuationPolicy,
) -> tuple[
    bool,
    list[str],
]:
    """
    시장가격을 검사합니다.
    """

    errors: list[str] = []

    if not is_valid_number(
        price
    ):
        errors.append(
            "가격이 유효한 숫자가 아닙니다."
        )

        return (
            False,
            errors,
        )

    numeric_price = float(
        price
    )

    if numeric_price == 0:
        if not policy.allow_zero_position_price:
            errors.append(
                "가격이 0입니다."
            )

    elif numeric_price < policy.minimum_valid_price:
        errors.append(
            "가격이 Minimum Valid Price보다 낮습니다."
        )

    if numeric_price > policy.maximum_valid_price:
        errors.append(
            "가격이 Maximum Valid Price보다 높습니다."
        )

    return (
        not errors,
        errors,
    )


def extract_latest_close(
    history: pd.DataFrame,
) -> float:
    """
    시장 데이터 DataFrame에서 최신 종가를 추출합니다.
    """

    if not isinstance(
        history,
        pd.DataFrame,
    ):
        raise TypeError(
            "Market History가 DataFrame 형식이 아닙니다."
        )

    if history.empty:
        raise RuntimeError(
            "Market History가 비어 있습니다."
        )

    if "Close" not in history.columns:
        raise RuntimeError(
            "Market History에 Close 열이 없습니다."
        )

    close_series = history[
        "Close"
    ].dropna()

    if close_series.empty:
        raise RuntimeError(
            "Market History의 Close 값이 모두 비어 있습니다."
        )

    latest_value = close_series.iloc[
        -1
    ]

    if isinstance(
        latest_value,
        pd.Series,
    ):
        if latest_value.empty:
            raise RuntimeError(
                "최신 Close Series가 비어 있습니다."
            )

        latest_value = latest_value.iloc[
            0
        ]

    if not is_valid_number(
        latest_value
    ):
        raise RuntimeError(
            "최신 Close 값이 유효한 숫자가 아닙니다."
        )

    return round_price(
        float(latest_value)
    )


def fetch_latest_market_price(
    symbol: str,
    period: str = "5d",
    interval: str = "1d",
) -> float:
    """
    data.market.get_history()를 이용해 최신 종가를 가져옵니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    history = get_history(
        symbol=normalized_symbol,
        period=period,
        interval=interval,
    )

    return extract_latest_close(
        history
    )


def normalize_provided_prices(
    latest_prices: dict[
        str,
        float,
    ] | None,
) -> dict[
    str,
    float,
]:
    """
    사용자가 제공한 가격 Dictionary를 정규화합니다.
    """

    if latest_prices is None:
        return {}

    if not isinstance(
        latest_prices,
        dict,
    ):
        raise TypeError(
            "latest_prices는 Dictionary 형식이어야 합니다."
        )

    normalized: dict[
        str,
        float,
    ] = {}

    for symbol, price in latest_prices.items():
        normalized_symbol = normalize_symbol(
            symbol
        )

        if not is_valid_number(
            price
        ):
            raise ValueError(
                f"{normalized_symbol} 가격이 유효하지 않습니다."
            )

        normalized[
            normalized_symbol
        ] = round_price(
            float(price)
        )

    return normalized


def resolve_latest_price(
    symbol: str,
    position: PaperPosition,
    provided_prices: dict[
        str,
        float,
    ],
    policy: PaperPortfolioValuationPolicy,
) -> tuple[
    float | None,
    str,
    str,
    list[str],
]:
    """
    종목의 평가가격을 결정합니다.

    우선순위:

    1. 사용자가 제공한 가격
    2. Market Data
    3. Position 저장가격
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    errors: list[str] = []

    if normalized_symbol in provided_prices:
        return (
            provided_prices[
                normalized_symbol
            ],
            "PROVIDED",
            "사용자 제공 최신 가격",
            errors,
        )

    try:
        market_price = fetch_latest_market_price(
            symbol=normalized_symbol,
            period=policy.price_period,
            interval=policy.price_interval,
        )

        return (
            market_price,
            "MARKET_DATA",
            "시장 데이터 최신 종가",
            errors,
        )

    except Exception as error:
        errors.append(
            f"시장가격 조회 실패: {error}"
        )

    if (
        policy.allow_position_price_fallback
        and is_valid_number(
            position.latest_price
        )
        and position.latest_price > 0
    ):
        return (
            round_price(
                position.latest_price
            ),
            "POSITION_PRICE",
            "기존 Position 저장 가격",
            errors,
        )

    return (
        None,
        "UNAVAILABLE",
        "사용 가능한 평가가격 없음",
        errors,
    )


def calculate_position_valuation(
    position: PaperPosition,
    latest_price: float | None,
    price_source: str,
    price_source_label: str,
    policy: PaperPortfolioValuationPolicy,
    resolution_errors: list[str] | None = None,
) -> PaperPositionValuation:
    """
    한 종목의 시장가치와 미실현 손익을 계산합니다.
    """

    symbol = normalize_symbol(
        position.symbol
    )

    reasons: list[str] = []
    warnings: list[str] = list(
        resolution_errors
        or []
    )

    previous_price = round_price(
        position.latest_price
    )

    previous_market_value = round_money(
        position.market_value
    )

    if position.shares <= 0:
        reasons.append(
            "보유 수량이 0이므로 FLAT Position입니다."
        )

        return PaperPositionValuation(
            symbol=symbol,

            valuation_status="FLAT",
            valuation_status_label=(
                "보유 Position 없음"
            ),

            position_state="FLAT",
            shares=0,

            average_price=0.0,
            cost_basis=0.0,

            previous_price=previous_price,
            latest_price=0.0,
            price_change=0.0,
            price_change_percent=0.0,

            price_source="NOT_REQUIRED",
            price_source_label=(
                "FLAT Position은 가격 평가 불필요"
            ),

            previous_market_value=previous_market_value,
            market_value=0.0,
            market_value_change=round_money(
                -previous_market_value
            ),

            unrealized_pnl=0.0,
            unrealized_pnl_percent=0.0,
            realized_pnl=round_money(
                position.realized_pnl
            ),

            portfolio_weight_percent=0.0,

            price_loaded=True,
            price_valid=True,
            valuation_calculated=True,
            checks_passed=True,

            reasons=reasons,
            warnings=warnings,
        )

    if latest_price is None:
        warnings.append(
            "평가에 사용할 최신 가격을 구하지 못했습니다."
        )

        return PaperPositionValuation(
            symbol=symbol,

            valuation_status="PRICE_MISSING",
            valuation_status_label=(
                "최신 가격 누락"
            ),

            position_state=position.state,
            shares=position.shares,

            average_price=round_price(
                position.average_price
            ),
            cost_basis=round_money(
                position.cost_basis
            ),

            previous_price=previous_price,
            latest_price=0.0,
            price_change=0.0,
            price_change_percent=0.0,

            price_source=price_source,
            price_source_label=price_source_label,

            previous_market_value=previous_market_value,
            market_value=previous_market_value,
            market_value_change=0.0,

            unrealized_pnl=round_money(
                position.unrealized_pnl
            ),
            unrealized_pnl_percent=round_percent(
                position.unrealized_pnl_percent
            ),
            realized_pnl=round_money(
                position.realized_pnl
            ),

            portfolio_weight_percent=0.0,

            price_loaded=False,
            price_valid=False,
            valuation_calculated=False,
            checks_passed=False,

            reasons=reasons,
            warnings=warnings,
        )

    (
        price_valid,
        price_errors,
    ) = validate_market_price(
        price=latest_price,
        policy=policy,
    )

    warnings.extend(
        price_errors
    )

    if not price_valid:
        return PaperPositionValuation(
            symbol=symbol,

            valuation_status="INVALID_PRICE",
            valuation_status_label=(
                "유효하지 않은 최신 가격"
            ),

            position_state=position.state,
            shares=position.shares,

            average_price=round_price(
                position.average_price
            ),
            cost_basis=round_money(
                position.cost_basis
            ),

            previous_price=previous_price,
            latest_price=round_price(
                latest_price
            ),
            price_change=0.0,
            price_change_percent=0.0,

            price_source=price_source,
            price_source_label=price_source_label,

            previous_market_value=previous_market_value,
            market_value=previous_market_value,
            market_value_change=0.0,

            unrealized_pnl=round_money(
                position.unrealized_pnl
            ),
            unrealized_pnl_percent=round_percent(
                position.unrealized_pnl_percent
            ),
            realized_pnl=round_money(
                position.realized_pnl
            ),

            portfolio_weight_percent=0.0,

            price_loaded=True,
            price_valid=False,
            valuation_calculated=False,
            checks_passed=False,

            reasons=reasons,
            warnings=warnings,
        )

    latest_price = round_price(
        latest_price
    )

    market_value = round_money(
        position.shares
        * latest_price
    )

    unrealized_pnl = round_money(
        market_value
        - position.cost_basis
    )

    if position.cost_basis > 0:
        unrealized_pnl_percent = round_percent(
            (
                unrealized_pnl
                / position.cost_basis
            )
            * 100.0
        )

    else:
        unrealized_pnl_percent = 0.0

    price_change = round_price(
        latest_price
        - previous_price
    )

    if previous_price > 0:
        price_change_percent = round_percent(
            (
                price_change
                / previous_price
            )
            * 100.0
        )

    else:
        price_change_percent = 0.0

    market_value_change = round_money(
        market_value
        - previous_market_value
    )

    reasons.extend(
        [
            (
                f"{symbol} 최신 가격은 "
                f"${latest_price:,.4f}입니다."
            ),
            (
                f"보유 수량은 {position.shares}주입니다."
            ),
            (
                f"평가 시장가치는 "
                f"${market_value:,.2f}입니다."
            ),
            (
                f"미실현 손익은 "
                f"${unrealized_pnl:,.2f}입니다."
            ),
        ]
    )

    return PaperPositionValuation(
        symbol=symbol,

        valuation_status="VALUED",
        valuation_status_label=(
            "최신 가격 평가 완료"
        ),

        position_state=position.state,
        shares=position.shares,

        average_price=round_price(
            position.average_price
        ),
        cost_basis=round_money(
            position.cost_basis
        ),

        previous_price=previous_price,
        latest_price=latest_price,
        price_change=price_change,
        price_change_percent=(
            price_change_percent
        ),

        price_source=price_source,
        price_source_label=price_source_label,

        previous_market_value=previous_market_value,
        market_value=market_value,
        market_value_change=market_value_change,

        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_percent=(
            unrealized_pnl_percent
        ),
        realized_pnl=round_money(
            position.realized_pnl
        ),

        portfolio_weight_percent=0.0,

        price_loaded=True,
        price_valid=True,
        valuation_calculated=True,
        checks_passed=True,

        reasons=reasons,
        warnings=warnings,
    )


def update_portfolio_position(
    portfolio: PaperPortfolioState,
    valuation: PaperPositionValuation,
) -> None:
    """
    Position Valuation 결과를 Portfolio State에 반영합니다.
    """

    if valuation.symbol not in portfolio.positions:
        return

    position = portfolio.positions[
        valuation.symbol
    ]

    if valuation.valuation_status == "VALUED":
        position.latest_price = round_price(
            valuation.latest_price
        )

        position.market_value = round_money(
            valuation.market_value
        )

        position.unrealized_pnl = round_money(
            valuation.unrealized_pnl
        )

        position.unrealized_pnl_percent = (
            round_percent(
                valuation.unrealized_pnl_percent
            )
        )

        position.updated_at = (
            datetime.now().isoformat()
        )

    elif valuation.valuation_status == "FLAT":
        position.state = "FLAT"
        position.shares = 0
        position.average_price = 0.0
        position.cost_basis = 0.0
        position.latest_price = 0.0
        position.market_value = 0.0
        position.unrealized_pnl = 0.0
        position.unrealized_pnl_percent = 0.0
        position.updated_at = (
            datetime.now().isoformat()
        )


def recalculate_valued_portfolio_totals(
    portfolio: PaperPortfolioState,
) -> None:
    """
    평가 후 Portfolio 합계를 다시 계산합니다.
    """

    portfolio.total_market_value = round_money(
        sum(
            position.market_value
            for position
            in portfolio.positions.values()
        )
    )

    portfolio.total_unrealized_pnl = round_money(
        sum(
            position.unrealized_pnl
            for position
            in portfolio.positions.values()
        )
    )

    portfolio.total_realized_pnl = round_money(
        sum(
            position.realized_pnl
            for position
            in portfolio.positions.values()
        )
    )

    portfolio.total_equity = round_money(
        portfolio.cash_balance
        + portfolio.total_market_value
    )

    portfolio.updated_at = (
        datetime.now().isoformat()
    )


def calculate_portfolio_weights(
    position_valuations: dict[
        str,
        PaperPositionValuation,
    ],
    total_equity: float,
    cash_balance: float,
) -> tuple[
    float,
    float,
]:
    """
    현금 비중과 투자 비중을 계산하고
    종목별 Portfolio Weight를 적용합니다.
    """

    if total_equity <= 0:
        for valuation in position_valuations.values():
            valuation.portfolio_weight_percent = 0.0

        return (
            0.0,
            0.0,
        )

    for valuation in position_valuations.values():
        valuation.portfolio_weight_percent = (
            round_percent(
                (
                    valuation.market_value
                    / total_equity
                )
                * 100.0
            )
        )

    cash_weight_percent = round_percent(
        (
            cash_balance
            / total_equity
        )
        * 100.0
    )

    invested_value = sum(
        valuation.market_value
        for valuation
        in position_valuations.values()
    )

    invested_weight_percent = round_percent(
        (
            invested_value
            / total_equity
        )
        * 100.0
    )

    return (
        cash_weight_percent,
        invested_weight_percent,
    )


def build_valuation_notes(
    valuation_status: str,
    policy: PaperPortfolioValuationPolicy,
    cash_weight_percent: float,
    invested_weight_percent: float,
    missing_price_symbols: list[str],
    invalid_price_symbols: list[str],
) -> tuple[
    list[str],
    list[str],
    list[str],
]:
    """
    Reasons, Warnings, Next Actions를 생성합니다.
    """

    reasons: list[str] = []
    warnings: list[str] = []

    if valuation_status == "VALUED":
        reasons.append(
            "모든 보유 Position을 최신 가격으로 평가했습니다."
        )

    elif valuation_status == "PARTIAL":
        reasons.append(
            "일부 Position만 최신 가격으로 평가했습니다."
        )

    elif valuation_status == "NO_POSITIONS":
        reasons.append(
            "평가할 Long Position이 없습니다."
        )

    elif valuation_status == "BLOCKED":
        reasons.append(
            "가격 또는 정책 검사 실패로 평가가 차단되었습니다."
        )

    else:
        reasons.append(
            "Portfolio Valuation을 완료하지 못했습니다."
        )

    if cash_weight_percent >= (
        policy.cash_weight_warning_percent
    ):
        warnings.append(
            (
                f"현금 비중이 {cash_weight_percent:.2f}%로 "
                "설정된 경고 기준보다 높습니다."
            )
        )

    if invested_weight_percent >= (
        policy.invested_weight_warning_percent
    ):
        warnings.append(
            (
                f"투자 비중이 {invested_weight_percent:.2f}%로 "
                "설정된 경고 기준보다 높습니다."
            )
        )

    if missing_price_symbols:
        warnings.append(
            (
                "최신 가격이 누락된 종목: "
                f"{', '.join(missing_price_symbols)}"
            )
        )

    if invalid_price_symbols:
        warnings.append(
            (
                "유효하지 않은 가격이 확인된 종목: "
                f"{', '.join(invalid_price_symbols)}"
            )
        )

    warnings.extend(
        [
            (
                "이 평가는 연구용 Paper Trading "
                "가상 Portfolio 평가입니다."
            ),
            (
                "실제 Broker 계좌 잔액이나 실제 Position을 "
                "조회하지 않습니다."
            ),
            (
                "실제 Broker API, 실제 주문 및 Live Execution은 "
                "모두 차단됩니다."
            ),
            (
                "시장 데이터는 지연되거나 조정될 수 있습니다."
            ),
        ]
    )

    if valuation_status in {
        "VALUED",
        "PARTIAL",
        "NO_POSITIONS",
    }:
        next_actions = [
            (
                "평가 Snapshot을 JSON 파일로 저장합니다."
            ),
            (
                "다음 거래일에 새로운 시장가격으로 "
                "다시 평가합니다."
            ),
            (
                "Portfolio Equity와 손익 변화를 "
                "시간순으로 기록합니다."
            ),
            (
                "V10.1 Portfolio Performance Tracker로 "
                "평가 결과를 전달합니다."
            ),
        ]

    else:
        next_actions = [
            (
                "누락되거나 잘못된 시장가격을 확인합니다."
            ),
            (
                "Portfolio State와 Valuation Policy를 "
                "다시 검증합니다."
            ),
            (
                "정상 가격이 확보된 후 다시 실행합니다."
            ),
        ]

    return (
        reasons,
        warnings,
        next_actions,
    )


def run_paper_portfolio_valuation(
    portfolio_state: PaperPortfolioState | None = None,
    latest_prices: dict[
        str,
        float,
    ] | None = None,
    valuation_policy: (
        PaperPortfolioValuationPolicy
        | None
    ) = None,
    initial_cash: float = 10_000.0,
) -> PaperPortfolioValuationResult:
    """
    V10.0 Paper Portfolio Valuation을 실행합니다.

    latest_prices 예시:

    {
        "AAPL": 340.50,
        "MSFT": 515.25,
    }

    실제 Broker 주문이나 Live Execution은 수행하지 않습니다.
    """

    policy = (
        valuation_policy
        if valuation_policy is not None
        else PaperPortfolioValuationPolicy()
    )

    (
        policy_valid,
        policy_errors,
    ) = validate_valuation_policy(
        policy
    )

    source_portfolio_file: str | None = None

    if portfolio_state is None:
        source_state_path = (
            PROJECT_ROOT
            / "output"
            / "trading_engine"
            / "paper_portfolio"
            / "paper_portfolio_state_latest.json"
        )

        if source_state_path.exists():
            source_portfolio_file = str(
                source_state_path
            )

        portfolio_state = load_latest_portfolio_state(
            initial_cash=initial_cash
        )

    working_portfolio = copy_portfolio_state(
        portfolio_state
    )

    (
        source_valid,
        source_errors,
    ) = validate_portfolio_state(
        working_portfolio
    )

    provided_prices = normalize_provided_prices(
        latest_prices
    )

    previous_total_market_value = round_money(
        working_portfolio.total_market_value
    )

    previous_total_unrealized_pnl = round_money(
        working_portfolio.total_unrealized_pnl
    )

    previous_total_equity = round_money(
        working_portfolio.total_equity
    )

    position_valuations: dict[
        str,
        PaperPositionValuation,
    ] = {}

    missing_price_symbols: list[str] = []
    invalid_price_symbols: list[str] = []

    long_position_count = 0
    flat_position_count = 0

    valued_position_count = 0
    missing_price_count = 0
    invalid_price_count = 0

    if source_valid and policy_valid:
        for symbol in sorted(
            working_portfolio.positions.keys()
        ):
            position = working_portfolio.positions[
                symbol
            ]

            if position.shares > 0:
                long_position_count += 1

                (
                    resolved_price,
                    price_source,
                    price_source_label,
                    resolution_errors,
                ) = resolve_latest_price(
                    symbol=symbol,
                    position=position,
                    provided_prices=provided_prices,
                    policy=policy,
                )

            else:
                flat_position_count += 1

                resolved_price = None
                price_source = "NOT_REQUIRED"
                price_source_label = (
                    "FLAT Position은 가격 평가 불필요"
                )
                resolution_errors = []

            valuation = calculate_position_valuation(
                position=position,
                latest_price=resolved_price,
                price_source=price_source,
                price_source_label=price_source_label,
                policy=policy,
                resolution_errors=resolution_errors,
            )

            position_valuations[
                symbol
            ] = valuation

            if valuation.valuation_status == "VALUED":
                valued_position_count += 1

            elif (
                valuation.valuation_status
                == "PRICE_MISSING"
            ):
                missing_price_count += 1
                missing_price_symbols.append(
                    symbol
                )

            elif (
                valuation.valuation_status
                == "INVALID_PRICE"
            ):
                invalid_price_count += 1
                invalid_price_symbols.append(
                    symbol
                )

    total_position_count = len(
        working_portfolio.positions
    )

    active_position_count = (
        long_position_count
    )

    price_checks_passed = (
        missing_price_count == 0
        and invalid_price_count == 0
    )

    if (
        not policy.require_all_prices
        and valued_position_count > 0
    ):
        price_checks_passed = True

    position_checks_passed = (
        source_valid
        and all(
            valuation.checks_passed
            or valuation.valuation_status
            in {
                "FLAT",
                "PRICE_MISSING",
                "INVALID_PRICE",
            }
            for valuation
            in position_valuations.values()
        )
    )

    portfolio_updated = False

    if (
        source_valid
        and policy_valid
        and (
            price_checks_passed
            or not policy.require_all_prices
        )
    ):
        for valuation in position_valuations.values():
            update_portfolio_position(
                portfolio=working_portfolio,
                valuation=valuation,
            )

        recalculate_valued_portfolio_totals(
            working_portfolio
        )

        portfolio_updated = True

    updated_total_market_value = round_money(
        working_portfolio.total_market_value
    )

    updated_total_unrealized_pnl = round_money(
        working_portfolio.total_unrealized_pnl
    )

    updated_total_equity = round_money(
        working_portfolio.total_equity
    )

    (
        cash_weight_percent,
        invested_weight_percent,
    ) = calculate_portfolio_weights(
        position_valuations=position_valuations,
        total_equity=updated_total_equity,
        cash_balance=working_portfolio.cash_balance,
    )

    total_market_value_change = round_money(
        updated_total_market_value
        - previous_total_market_value
    )

    total_unrealized_pnl_change = round_money(
        updated_total_unrealized_pnl
        - previous_total_unrealized_pnl
    )

    total_equity_change = round_money(
        updated_total_equity
        - previous_total_equity
    )

    if previous_total_equity > 0:
        total_equity_change_percent = round_percent(
            (
                total_equity_change
                / previous_total_equity
            )
            * 100.0
        )

    else:
        total_equity_change_percent = 0.0

    total_profit_loss = round_money(
        updated_total_equity
        - working_portfolio.initial_cash
    )

    if working_portfolio.initial_cash > 0:
        total_return_percent = round_percent(
            (
                total_profit_loss
                / working_portfolio.initial_cash
            )
            * 100.0
        )

    else:
        total_return_percent = 0.0

    expected_total_equity = round_money(
        working_portfolio.cash_balance
        + updated_total_market_value
    )

    total_checks_passed = (
        abs(
            updated_total_equity
            - expected_total_equity
        )
        <= 0.01
    )

    if not source_valid:
        valuation_status = "FAILED"
        valuation_status_label = (
            "Portfolio State 검사 실패"
        )

    elif not policy_valid:
        valuation_status = "FAILED"
        valuation_status_label = (
            "Valuation Policy 검사 실패"
        )

    elif active_position_count == 0:
        valuation_status = "NO_POSITIONS"
        valuation_status_label = (
            "평가할 Long Position 없음"
        )

    elif (
        policy.require_all_prices
        and not price_checks_passed
    ):
        valuation_status = "BLOCKED"
        valuation_status_label = (
            "필수 시장가격 검사 실패"
        )

    elif (
        valued_position_count
        == active_position_count
    ):
        valuation_status = "VALUED"
        valuation_status_label = (
            "모든 Position 평가 완료"
        )

    elif valued_position_count > 0:
        valuation_status = "PARTIAL"
        valuation_status_label = (
            "일부 Position 평가 완료"
        )

    else:
        valuation_status = "BLOCKED"
        valuation_status_label = (
            "평가 가능한 Position 없음"
        )

    all_checks_passed = (
        source_valid
        and policy_valid
        and position_checks_passed
        and total_checks_passed
        and (
            price_checks_passed
            or not policy.require_all_prices
            or active_position_count == 0
        )
        and valuation_status
        in {
            "VALUED",
            "PARTIAL",
            "NO_POSITIONS",
        }
    )

    (
        reasons,
        warnings,
        next_actions,
    ) = build_valuation_notes(
        valuation_status=valuation_status,
        policy=policy,
        cash_weight_percent=(
            cash_weight_percent
        ),
        invested_weight_percent=(
            invested_weight_percent
        ),
        missing_price_symbols=(
            missing_price_symbols
        ),
        invalid_price_symbols=(
            invalid_price_symbols
        ),
    )

    reasons.extend(
        [
            (
                f"초기 현금은 "
                f"${working_portfolio.initial_cash:,.2f}입니다."
            ),
            (
                f"현재 현금 잔액은 "
                f"${working_portfolio.cash_balance:,.2f}입니다."
            ),
            (
                f"평가 후 총 시장가치는 "
                f"${updated_total_market_value:,.2f}입니다."
            ),
            (
                f"평가 후 총 계좌가치는 "
                f"${updated_total_equity:,.2f}입니다."
            ),
            (
                f"총 수익률은 "
                f"{total_return_percent:.4f}%입니다."
            ),
            (
                f"현금 비중은 "
                f"{cash_weight_percent:.4f}%입니다."
            ),
            (
                f"투자 비중은 "
                f"{invested_weight_percent:.4f}%입니다."
            ),
        ]
    )

    warnings.extend(
        policy_errors
    )

    warnings.extend(
        source_errors
    )

    result = PaperPortfolioValuationResult(
        version="V10.0",
        created_at=datetime.now().isoformat(),

        valuation_id=str(
            uuid.uuid4()
        ),
        portfolio_id=(
            working_portfolio.portfolio_id
        ),

        valuation_status=valuation_status,
        valuation_status_label=(
            valuation_status_label
        ),

        source_portfolio_file=(
            source_portfolio_file
        ),

        initial_cash=round_money(
            working_portfolio.initial_cash
        ),
        cash_balance=round_money(
            working_portfolio.cash_balance
        ),

        previous_total_market_value=(
            previous_total_market_value
        ),
        updated_total_market_value=(
            updated_total_market_value
        ),
        total_market_value_change=(
            total_market_value_change
        ),

        previous_total_unrealized_pnl=(
            previous_total_unrealized_pnl
        ),
        updated_total_unrealized_pnl=(
            updated_total_unrealized_pnl
        ),
        total_unrealized_pnl_change=(
            total_unrealized_pnl_change
        ),

        total_realized_pnl=round_money(
            working_portfolio.total_realized_pnl
        ),
        total_commission=round_money(
            working_portfolio.total_commission
        ),

        previous_total_equity=(
            previous_total_equity
        ),
        updated_total_equity=(
            updated_total_equity
        ),
        total_equity_change=(
            total_equity_change
        ),
        total_equity_change_percent=(
            total_equity_change_percent
        ),

        total_profit_loss=(
            total_profit_loss
        ),
        total_return_percent=(
            total_return_percent
        ),

        cash_weight_percent=(
            cash_weight_percent
        ),
        invested_weight_percent=(
            invested_weight_percent
        ),

        position_count=(
            total_position_count
        ),
        long_position_count=(
            long_position_count
        ),
        flat_position_count=(
            flat_position_count
        ),

        valued_position_count=(
            valued_position_count
        ),
        missing_price_count=(
            missing_price_count
        ),
        invalid_price_count=(
            invalid_price_count
        ),

        source_loaded=True,
        source_valid=source_valid,

        policy_checks_passed=(
            policy_valid
        ),
        price_checks_passed=(
            price_checks_passed
        ),
        position_checks_passed=(
            position_checks_passed
        ),
        total_checks_passed=(
            total_checks_passed
        ),
        all_checks_passed=(
            all_checks_passed
        ),

        portfolio_updated=(
            portfolio_updated
        ),

        execution_blocked=True,
        broker_api_called=False,
        broker_order_created=False,
        live_order_created=False,
        live_execution_authorized=False,

        valuation_policy=policy,
        position_valuations=(
            position_valuations
        ),

        updated_portfolio_state=(
            working_portfolio
        ),

        reasons=reasons,
        warnings=warnings,
        next_actions=next_actions,
    )

    print_paper_portfolio_valuation(
        result
    )

    return result


def save_paper_portfolio_valuation(
    result: PaperPortfolioValuationResult,
) -> tuple[
    Path,
    Path,
    Path,
    Path,
]:
    """
    V10.0 평가 결과와 Snapshot을 JSON으로 저장합니다.
    """

    PAPER_VALUATION_OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        PAPER_VALUATION_OUTPUT_DIRECTORY
        / (
            "paper_portfolio_valuation_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        PAPER_VALUATION_OUTPUT_DIRECTORY
        / "paper_portfolio_valuation_latest.json"
    )

    snapshot_path = (
        PAPER_VALUATION_OUTPUT_DIRECTORY
        / (
            "paper_portfolio_snapshot_"
            f"{timestamp}.json"
        )
    )

    updated_state_path = (
        PROJECT_ROOT
        / "output"
        / "trading_engine"
        / "paper_portfolio"
        / "paper_portfolio_state_latest.json"
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

    result.snapshot_path = str(
        snapshot_path
    )

    result.updated_state_path = str(
        updated_state_path
    )

    payload = result.to_dict()

    snapshot_payload = {
        "version": result.version,
        "created_at": result.created_at,
        "valuation_id": result.valuation_id,
        "portfolio_id": result.portfolio_id,
        "valuation_status": (
            result.valuation_status
        ),
        "cash_balance": (
            result.cash_balance
        ),
        "total_market_value": (
            result.updated_total_market_value
        ),
        "total_equity": (
            result.updated_total_equity
        ),
        "total_unrealized_pnl": (
            result.updated_total_unrealized_pnl
        ),
        "total_realized_pnl": (
            result.total_realized_pnl
        ),
        "total_profit_loss": (
            result.total_profit_loss
        ),
        "total_return_percent": (
            result.total_return_percent
        ),
        "cash_weight_percent": (
            result.cash_weight_percent
        ),
        "invested_weight_percent": (
            result.invested_weight_percent
        ),
        "position_valuations": {
            symbol: valuation.to_dict()
            for symbol, valuation
            in result.position_valuations.items()
        },
    }

    write_json_file(
        report_path,
        payload,
    )

    write_json_file(
        latest_path,
        payload,
    )

    write_json_file(
        snapshot_path,
        snapshot_payload,
    )

    write_json_file(
        updated_state_path,
        result.updated_portfolio_state.to_dict(),
    )

    return (
        report_path,
        latest_path,
        snapshot_path,
        updated_state_path,
    )


def load_latest_valuation_result() -> dict[
    str,
    Any,
]:
    """
    저장된 최신 V10.0 평가 JSON을 읽습니다.
    """

    latest_path = (
        PAPER_VALUATION_OUTPUT_DIRECTORY
        / "paper_portfolio_valuation_latest.json"
    )

    return read_json_file(
        latest_path
    )


def load_valuation_portfolio_state(
    file_path: Path | None = None,
) -> PaperPortfolioState:
    """
    Valuation 결과에 저장된 Portfolio State를 불러옵니다.
    """

    target_path = (
        file_path
        if file_path is not None
        else (
            PAPER_VALUATION_OUTPUT_DIRECTORY
            / "paper_portfolio_valuation_latest.json"
        )
    )

    payload = read_json_file(
        target_path
    )

    state_payload = payload.get(
        "updated_portfolio_state"
    )

    if not isinstance(
        state_payload,
        dict,
    ):
        raise RuntimeError(
            "Valuation JSON에 updated_portfolio_state가 "
            "없습니다."
        )

    portfolio = portfolio_from_dict(
        state_payload
    )

    (
        valid,
        errors,
    ) = validate_portfolio_state(
        portfolio
    )

    if not valid:
        raise RuntimeError(
            "Valuation Portfolio State가 유효하지 않습니다: "
            f"{errors}"
        )

    return portfolio


def print_paper_portfolio_valuation(
    result: PaperPortfolioValuationResult,
) -> None:
    """
    V10.0 Paper Portfolio Valuation 결과를 출력합니다.
    """

    line_length = 140

    print()
    print("=" * line_length)
    print(
        "V10.0 PAPER PORTFOLIO VALUATION"
    )
    print("=" * line_length)

    print(
        f"Valuation status               : "
        f"{result.valuation_status}"
    )

    print(
        f"Valuation status label         : "
        f"{result.valuation_status_label}"
    )

    print(
        f"Valuation ID                   : "
        f"{result.valuation_id}"
    )

    print(
        f"Portfolio ID                   : "
        f"{result.portfolio_id}"
    )

    print()
    print("PORTFOLIO SUMMARY")
    print("-" * line_length)

    print(
        f"Initial cash                   : "
        f"${result.initial_cash:,.2f}"
    )

    print(
        f"Cash balance                   : "
        f"${result.cash_balance:,.2f}"
    )

    print(
        f"Previous market value          : "
        f"${result.previous_total_market_value:,.2f}"
    )

    print(
        f"Updated market value           : "
        f"${result.updated_total_market_value:,.2f}"
    )

    print(
        f"Market value change            : "
        f"${result.total_market_value_change:,.2f}"
    )

    print(
        f"Previous total equity          : "
        f"${result.previous_total_equity:,.2f}"
    )

    print(
        f"Updated total equity           : "
        f"${result.updated_total_equity:,.2f}"
    )

    print(
        f"Total equity change            : "
        f"${result.total_equity_change:,.2f}"
    )

    print(
        f"Total equity change %          : "
        f"{result.total_equity_change_percent:.4f}%"
    )

    print()
    print("PROFIT AND LOSS")
    print("-" * line_length)

    print(
        f"Previous unrealized PnL        : "
        f"${result.previous_total_unrealized_pnl:,.2f}"
    )

    print(
        f"Updated unrealized PnL         : "
        f"${result.updated_total_unrealized_pnl:,.2f}"
    )

    print(
        f"Unrealized PnL change          : "
        f"${result.total_unrealized_pnl_change:,.2f}"
    )

    print(
        f"Total realized PnL             : "
        f"${result.total_realized_pnl:,.2f}"
    )

    print(
        f"Total commission               : "
        f"${result.total_commission:,.2f}"
    )

    print(
        f"Total profit/loss              : "
        f"${result.total_profit_loss:,.2f}"
    )

    print(
        f"Total return                   : "
        f"{result.total_return_percent:.4f}%"
    )

    print()
    print("ALLOCATION")
    print("-" * line_length)

    print(
        f"Cash weight                    : "
        f"{result.cash_weight_percent:.4f}%"
    )

    print(
        f"Invested weight                : "
        f"{result.invested_weight_percent:.4f}%"
    )

    print()
    print("POSITION COUNTS")
    print("-" * line_length)

    print(
        f"Total positions                : "
        f"{result.position_count}"
    )

    print(
        f"Long positions                 : "
        f"{result.long_position_count}"
    )

    print(
        f"Flat positions                 : "
        f"{result.flat_position_count}"
    )

    print(
        f"Valued positions               : "
        f"{result.valued_position_count}"
    )

    print(
        f"Missing prices                 : "
        f"{result.missing_price_count}"
    )

    print(
        f"Invalid prices                 : "
        f"{result.invalid_price_count}"
    )

    if result.position_valuations:
        print()
        print("POSITION VALUATIONS")
        print("-" * line_length)

        for symbol, valuation in (
            result.position_valuations.items()
        ):
            print()
            print(
                f"[{symbol}]"
            )

            print(
                f"Status                         : "
                f"{valuation.valuation_status}"
            )

            print(
                f"State                          : "
                f"{valuation.position_state}"
            )

            print(
                f"Shares                         : "
                f"{valuation.shares}"
            )

            print(
                f"Average price                  : "
                f"${valuation.average_price:,.4f}"
            )

            print(
                f"Previous price                 : "
                f"${valuation.previous_price:,.4f}"
            )

            print(
                f"Latest price                   : "
                f"${valuation.latest_price:,.4f}"
            )

            print(
                f"Price change                   : "
                f"${valuation.price_change:,.4f}"
            )

            print(
                f"Price change %                 : "
                f"{valuation.price_change_percent:.4f}%"
            )

            print(
                f"Price source                   : "
                f"{valuation.price_source}"
            )

            print(
                f"Market value                   : "
                f"${valuation.market_value:,.2f}"
            )

            print(
                f"Unrealized PnL                 : "
                f"${valuation.unrealized_pnl:,.2f}"
            )

            print(
                f"Unrealized PnL %               : "
                f"{valuation.unrealized_pnl_percent:.4f}%"
            )

            print(
                f"Realized PnL                   : "
                f"${valuation.realized_pnl:,.2f}"
            )

            print(
                f"Portfolio weight               : "
                f"{valuation.portfolio_weight_percent:.4f}%"
            )

    print()
    print("VALIDATION")
    print("-" * line_length)

    print(
        f"Source loaded                  : "
        f"{result.source_loaded}"
    )

    print(
        f"Source valid                   : "
        f"{result.source_valid}"
    )

    print(
        f"Policy checks passed           : "
        f"{result.policy_checks_passed}"
    )

    print(
        f"Price checks passed            : "
        f"{result.price_checks_passed}"
    )

    print(
        f"Position checks passed         : "
        f"{result.position_checks_passed}"
    )

    print(
        f"Total checks passed            : "
        f"{result.total_checks_passed}"
    )

    print(
        f"Portfolio updated              : "
        f"{result.portfolio_updated}"
    )

    print(
        f"All checks passed              : "
        f"{result.all_checks_passed}"
    )

    print()
    print("EXECUTION SAFETY")
    print("-" * line_length)

    print(
        f"Execution blocked              : "
        f"{result.execution_blocked}"
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

    if result.reasons:
        print()
        print("REASONS")
        print("-" * line_length)

        for reason in result.reasons:
            print(
                f"- {reason}"
            )

    if result.warnings:
        print()
        print("WARNINGS")
        print("-" * line_length)

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    if result.next_actions:
        print()
        print("NEXT ACTIONS")
        print("-" * line_length)

        for action in result.next_actions:
            print(
                f"- {action}"
            )

    print()
    print("FILES")
    print("-" * line_length)

    print(
        f"Source portfolio file          : "
        f"{result.source_portfolio_file}"
    )

    print(
        f"Report file                    : "
        f"{result.report_path or 'Not saved yet'}"
    )

    print(
        f"Latest file                    : "
        f"{result.latest_path or 'Not saved yet'}"
    )

    print(
        f"Snapshot file                  : "
        f"{result.snapshot_path or 'Not saved yet'}"
    )

    print(
        f"Updated state file             : "
        f"{result.updated_state_path or 'Not saved yet'}"
    )

    print("=" * line_length)

    print(
        "주의: 이 결과는 연구용 Paper Trading "
        "Portfolio 평가이며 실제 계좌 조회나 "
        "증권 주문을 수행하지 않습니다."
    )