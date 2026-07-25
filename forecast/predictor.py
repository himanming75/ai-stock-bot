import math
from dataclasses import asdict, dataclass

import pandas as pd


@dataclass
class TradePlan:
    """
    한 종목의 기술적 매매 계획입니다.
    """

    symbol: str
    current_price: float

    entry_low: float
    entry_high: float

    stop_loss: float
    target_1: float
    target_2: float

    expected_gain_1: float
    expected_gain_2: float
    expected_loss: float

    risk_reward_1: float
    risk_reward_2: float

    atr: float
    volatility_percent: float
    holding_period: str

    plan_status: str

    def to_dict(self) -> dict:
        """
        JSON 저장에 사용할 수 있도록 딕셔너리로 변환합니다.
        """

        return asdict(self)


def calculate_atr(
    data: pd.DataFrame,
    period: int = 14,
) -> pd.Series:
    """
    ATR(Average True Range)을 계산합니다.

    ATR은 최근 가격의 평균 변동폭을 나타냅니다.
    값이 클수록 변동성이 큰 종목입니다.
    """

    required_columns = {
        "High",
        "Low",
        "Close",
    }

    missing_columns = (
        required_columns
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "ATR 계산에 필요한 컬럼이 없습니다: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    if period <= 0:
        raise ValueError(
            "ATR period는 0보다 커야 합니다."
        )

    previous_close = (
        data["Close"]
        .shift(1)
    )

    high_low = (
        data["High"]
        - data["Low"]
    ).abs()

    high_previous_close = (
        data["High"]
        - previous_close
    ).abs()

    low_previous_close = (
        data["Low"]
        - previous_close
    ).abs()

    true_range = pd.concat(
        [
            high_low,
            high_previous_close,
            low_previous_close,
        ],
        axis=1,
    ).max(axis=1)

    atr = true_range.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    return atr


def safe_percent_change(
    new_value: float,
    base_value: float,
) -> float:
    """
    기준값 대비 변동률을 계산합니다.
    """

    if base_value <= 0:
        return 0.0

    return (
        (new_value / base_value) - 1
    ) * 100


def safe_risk_reward(
    entry_price: float,
    target_price: float,
    stop_loss: float,
) -> float:
    """
    Risk/Reward 비율을 계산합니다.

    예:
    예상 수익 $10
    예상 손실 $5

    Risk/Reward = 2.0
    """

    potential_reward = (
        target_price - entry_price
    )

    potential_risk = (
        entry_price - stop_loss
    )

    if potential_risk <= 0:
        return 0.0

    return (
        potential_reward
        / potential_risk
    )


def determine_holding_period(
    volatility_percent: float,
) -> str:
    """
    ATR 변동성을 기준으로 예상 보유기간을 분류합니다.
    """

    if volatility_percent >= 4:
        return "3 to 10 trading days"

    if volatility_percent >= 2:
        return "1 to 4 weeks"

    return "2 to 8 weeks"


def determine_plan_status(
    technical_signal: str,
    risk_reward_1: float,
    risk_reward_2: float,
) -> str:
    """
    매매계획의 사용 가능성을 분류합니다.
    """

    signal = (
        str(technical_signal)
        .upper()
        .strip()
    )

    if signal == "SELL":
        return "AVOID"

    if (
        signal == "BUY"
        and risk_reward_2 >= 2
    ):
        return "ATTRACTIVE"

    if (
        signal in {"BUY", "HOLD"}
        and risk_reward_1 >= 1.5
    ):
        return "WATCH"

    return "WEAK"


def create_trade_plan(
    symbol: str,
    data: pd.DataFrame,
    technical_signal: str,
) -> TradePlan:
    """
    실제 가격과 변동성을 사용하여
    진입가, 손절가, 목표가를 계산합니다.

    계산 기준:
    - 진입 구간: 현재가와 MA5 주변
    - 손절가: 진입 기준가 - 1.5 ATR
    - 1차 목표가: 진입 기준가 + 2 ATR
    - 2차 목표가: 진입 기준가 + 3 ATR
    """

    if data is None or data.empty:
        raise ValueError(
            "매매계획을 계산할 데이터가 없습니다."
        )

    symbol = (
        str(symbol)
        .upper()
        .strip()
    )

    if not symbol:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    required_columns = {
        "Close",
        "High",
        "Low",
        "MA5",
        "MA20",
        "BB_UPPER",
        "BB_MIDDLE",
        "BB_LOWER",
    }

    missing_columns = (
        required_columns
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "매매계획에 필요한 컬럼이 없습니다: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    working_data = data.copy()

    working_data["ATR"] = calculate_atr(
        working_data,
        period=14,
    )

    working_data = working_data.dropna(
        subset=["ATR"]
    )

    if working_data.empty:
        raise ValueError(
            "ATR 계산 후 사용할 데이터가 없습니다."
        )

    latest = working_data.iloc[-1]

    current_price = float(
        latest["Close"]
    )

    ma5 = float(
        latest["MA5"]
    )

    ma20 = float(
        latest["MA20"]
    )

    bb_upper = float(
        latest["BB_UPPER"]
    )

    atr = float(
        latest["ATR"]
    )

    if not math.isfinite(atr) or atr <= 0:
        raise ValueError(
            f"ATR 값이 올바르지 않습니다: {atr}"
        )

    # 현재가와 MA5 중 낮은 값을 중심으로
    # 추격매수를 줄이기 위한 진입 구간 계산
    entry_center = min(
        current_price,
        ma5,
    )

    entry_low = max(
        ma20,
        entry_center - 0.35 * atr,
    )

    entry_high = min(
        current_price,
        entry_center + 0.35 * atr,
    )

    if entry_low > entry_high:
        entry_low = min(
            entry_center,
            current_price,
        )

        entry_high = max(
            entry_center,
            current_price,
        )

    reference_entry = (
        entry_low + entry_high
    ) / 2

    stop_loss = max(
        0.01,
        reference_entry - 1.5 * atr,
    )

    target_1 = (
        reference_entry + 2 * atr
    )

    target_2 = (
        reference_entry + 3 * atr
    )

    # 볼린저 상단이 가까운 경우
    # 1차 목표가가 지나치게 높아지지 않도록 조정
    if bb_upper > reference_entry:
        target_1 = min(
            target_1,
            bb_upper,
        )

    # 2차 목표가는 1차 목표가보다 반드시 높게 유지
    target_2 = max(
        target_2,
        target_1 + 0.5 * atr,
    )

    expected_gain_1 = safe_percent_change(
        target_1,
        reference_entry,
    )

    expected_gain_2 = safe_percent_change(
        target_2,
        reference_entry,
    )

    expected_loss = abs(
        safe_percent_change(
            stop_loss,
            reference_entry,
        )
    )

    risk_reward_1 = safe_risk_reward(
        entry_price=reference_entry,
        target_price=target_1,
        stop_loss=stop_loss,
    )

    risk_reward_2 = safe_risk_reward(
        entry_price=reference_entry,
        target_price=target_2,
        stop_loss=stop_loss,
    )

    volatility_percent = (
        atr / current_price
    ) * 100

    holding_period = determine_holding_period(
        volatility_percent
    )

    plan_status = determine_plan_status(
        technical_signal=technical_signal,
        risk_reward_1=risk_reward_1,
        risk_reward_2=risk_reward_2,
    )

    return TradePlan(
        symbol=symbol,
        current_price=round(
            current_price,
            2,
        ),
        entry_low=round(
            entry_low,
            2,
        ),
        entry_high=round(
            entry_high,
            2,
        ),
        stop_loss=round(
            stop_loss,
            2,
        ),
        target_1=round(
            target_1,
            2,
        ),
        target_2=round(
            target_2,
            2,
        ),
        expected_gain_1=round(
            expected_gain_1,
            2,
        ),
        expected_gain_2=round(
            expected_gain_2,
            2,
        ),
        expected_loss=round(
            expected_loss,
            2,
        ),
        risk_reward_1=round(
            risk_reward_1,
            2,
        ),
        risk_reward_2=round(
            risk_reward_2,
            2,
        ),
        atr=round(
            atr,
            2,
        ),
        volatility_percent=round(
            volatility_percent,
            2,
        ),
        holding_period=holding_period,
        plan_status=plan_status,
    )


def print_trade_plan(
    plan: TradePlan,
) -> None:
    """
    매매계획을 터미널에 보기 좋게 출력합니다.
    """

    print()
    print("=" * 60)
    print(
        f"{plan.symbol} TECHNICAL TRADE PLAN"
    )
    print("=" * 60)

    print(
        f"Plan status      : "
        f"{plan.plan_status}"
    )

    print(
        f"Current price    : "
        f"${plan.current_price:,.2f}"
    )

    print(
        f"Entry zone       : "
        f"${plan.entry_low:,.2f}"
        f" - "
        f"${plan.entry_high:,.2f}"
    )

    print(
        f"Stop loss        : "
        f"${plan.stop_loss:,.2f}"
    )

    print(
        f"Target 1         : "
        f"${plan.target_1:,.2f}"
    )

    print(
        f"Target 2         : "
        f"${plan.target_2:,.2f}"
    )

    print(
        f"Expected gain 1  : "
        f"{plan.expected_gain_1:.2f}%"
    )

    print(
        f"Expected gain 2  : "
        f"{plan.expected_gain_2:.2f}%"
    )

    print(
        f"Expected loss    : "
        f"{plan.expected_loss:.2f}%"
    )

    print(
        f"Risk/Reward 1    : "
        f"{plan.risk_reward_1:.2f}"
    )

    print(
        f"Risk/Reward 2    : "
        f"{plan.risk_reward_2:.2f}"
    )

    print(
        f"ATR              : "
        f"${plan.atr:,.2f}"
    )

    print(
        f"Volatility       : "
        f"{plan.volatility_percent:.2f}%"
    )

    print(
        f"Holding period   : "
        f"{plan.holding_period}"
    )

    print("-" * 60)
    print(
        "This is a technical planning model, "
        "not a prediction or investment guarantee."
    )