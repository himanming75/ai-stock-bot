from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import json
import numpy as np
import pandas as pd

from data.market import get_history


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
)


@dataclass
class BacktestTrade:
    """
    한 번의 완결된 매매 기록입니다.
    """

    symbol: str

    entry_date: str
    exit_date: str

    entry_price: float
    exit_price: float

    shares: int

    entry_score: float
    entry_signal: str

    stop_loss: float
    target_price: float

    exit_reason: str

    invested_amount: float
    profit_loss: float
    return_percent: float

    holding_days: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyBacktestResult:
    """
    종목별 추천 전략 백테스트 결과입니다.
    """

    symbol: str
    success: bool

    started_at: str
    finished_at: str

    data_start_date: str | None
    data_end_date: str | None

    initial_cash: float
    final_value: float

    total_return_percent: float
    buy_hold_return_percent: float

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_percent: float

    average_trade_return_percent: float
    average_win_percent: float
    average_loss_percent: float

    best_trade_percent: float
    worst_trade_percent: float

    maximum_drawdown_percent: float
    sharpe_ratio: float
    profit_factor: float

    average_holding_days: float

    trades: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]

    settings: dict[str, Any]

    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    값을 안전하게 float로 변환합니다.
    """

    try:
        converted = float(value)

        if np.isnan(converted):
            return default

        return converted

    except (
        TypeError,
        ValueError,
    ):
        return default


def normalize_symbol(
    symbol: str,
) -> str:
    """
    종목 코드를 대문자로 정리합니다.
    """

    normalized = (
        str(symbol)
        .upper()
        .strip()
    )

    if not normalized:
        raise ValueError(
            "종목 코드가 비어 있습니다."
        )

    return normalized


def prepare_backtest_data(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    백테스트에 필요한 기술지표를 계산합니다.

    미래 데이터를 사용하지 않고,
    각 날짜까지 확인 가능한 가격만 사용합니다.
    """

    if data is None or data.empty:
        raise ValueError(
            "백테스트 시장 데이터가 비어 있습니다."
        )

    required_columns = {
        "Open",
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
            "필요한 시장 데이터 열이 없습니다: "
            f"{sorted(missing_columns)}"
        )

    prepared = data.copy()

    for column in (
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ):
        if column in prepared.columns:
            prepared[column] = pd.to_numeric(
                prepared[column],
                errors="coerce",
            )

    # 이동평균
    prepared["MA5"] = (
        prepared["Close"]
        .rolling(
            window=5,
            min_periods=5,
        )
        .mean()
    )

    prepared["MA20"] = (
        prepared["Close"]
        .rolling(
            window=20,
            min_periods=20,
        )
        .mean()
    )

    prepared["MA50"] = (
        prepared["Close"]
        .rolling(
            window=50,
            min_periods=50,
        )
        .mean()
    )

    # RSI 14
    price_change = (
        prepared["Close"]
        .diff()
    )

    gain = price_change.clip(
        lower=0.0
    )

    loss = (
        -price_change.clip(
            upper=0.0
        )
    )

    average_gain = (
        gain.ewm(
            alpha=1 / 14,
            adjust=False,
            min_periods=14,
        )
        .mean()
    )

    average_loss = (
        loss.ewm(
            alpha=1 / 14,
            adjust=False,
            min_periods=14,
        )
        .mean()
    )

    relative_strength = (
        average_gain
        / average_loss.replace(
            0.0,
            np.nan,
        )
    )

    prepared["RSI14"] = (
        100.0
        - (
            100.0
            / (
                1.0
                + relative_strength
            )
        )
    )

    # MACD
    ema12 = (
        prepared["Close"]
        .ewm(
            span=12,
            adjust=False,
        )
        .mean()
    )

    ema26 = (
        prepared["Close"]
        .ewm(
            span=26,
            adjust=False,
        )
        .mean()
    )

    prepared["MACD"] = (
        ema12
        - ema26
    )

    prepared["MACD_SIGNAL"] = (
        prepared["MACD"]
        .ewm(
            span=9,
            adjust=False,
        )
        .mean()
    )

    prepared["MACD_HIST"] = (
        prepared["MACD"]
        - prepared["MACD_SIGNAL"]
    )

    # Bollinger Bands
    prepared["BB_MIDDLE"] = (
        prepared["Close"]
        .rolling(
            window=20,
            min_periods=20,
        )
        .mean()
    )

    rolling_std = (
        prepared["Close"]
        .rolling(
            window=20,
            min_periods=20,
        )
        .std()
    )

    prepared["BB_UPPER"] = (
        prepared["BB_MIDDLE"]
        + (
            rolling_std * 2.0
        )
    )

    prepared["BB_LOWER"] = (
        prepared["BB_MIDDLE"]
        - (
            rolling_std * 2.0
        )
    )

    # ATR 14
    previous_close = (
        prepared["Close"]
        .shift(1)
    )

    true_range = pd.concat(
        [
            (
                prepared["High"]
                - prepared["Low"]
            ).abs(),

            (
                prepared["High"]
                - previous_close
            ).abs(),

            (
                prepared["Low"]
                - previous_close
            ).abs(),
        ],
        axis=1,
    ).max(
        axis=1
    )

    prepared["ATR14"] = (
        true_range
        .rolling(
            window=14,
            min_periods=14,
        )
        .mean()
    )

    # 거래량 평균
    if "Volume" in prepared.columns:
        prepared["VOLUME_MA20"] = (
            prepared["Volume"]
            .rolling(
                window=20,
                min_periods=20,
            )
            .mean()
        )

    else:
        prepared["Volume"] = 0.0
        prepared["VOLUME_MA20"] = 0.0

    prepared = prepared.replace(
        [
            np.inf,
            -np.inf,
        ],
        np.nan,
    )

    prepared = prepared.dropna(
        subset=[
            "Open",
            "High",
            "Low",
            "Close",
            "MA5",
            "MA20",
            "MA50",
            "RSI14",
            "MACD",
            "MACD_SIGNAL",
            "MACD_HIST",
            "BB_UPPER",
            "BB_LOWER",
            "ATR14",
        ]
    )

    if prepared.empty:
        raise ValueError(
            "기술지표 계산 후 사용할 데이터가 없습니다."
        )

    return prepared


def calculate_historical_score(
    row: pd.Series,
) -> float:
    """
    해당 날짜까지 알려진 기술지표만 사용하여
    0~100점 추천 점수를 계산합니다.
    """

    score = 50.0

    close = safe_float(
        row.get(
            "Close"
        )
    )

    ma5 = safe_float(
        row.get(
            "MA5"
        )
    )

    ma20 = safe_float(
        row.get(
            "MA20"
        )
    )

    ma50 = safe_float(
        row.get(
            "MA50"
        )
    )

    rsi = safe_float(
        row.get(
            "RSI14"
        ),
        50.0,
    )

    macd = safe_float(
        row.get(
            "MACD"
        )
    )

    macd_signal = safe_float(
        row.get(
            "MACD_SIGNAL"
        )
    )

    macd_hist = safe_float(
        row.get(
            "MACD_HIST"
        )
    )

    bb_upper = safe_float(
        row.get(
            "BB_UPPER"
        )
    )

    bb_lower = safe_float(
        row.get(
            "BB_LOWER"
        )
    )

    volume = safe_float(
        row.get(
            "Volume"
        )
    )

    volume_ma20 = safe_float(
        row.get(
            "VOLUME_MA20"
        )
    )

    # 이동평균 추세
    if close > ma20:
        score += 8.0

    else:
        score -= 8.0

    if ma5 > ma20:
        score += 10.0

    else:
        score -= 6.0

    if ma20 > ma50:
        score += 10.0

    else:
        score -= 8.0

    # RSI
    if 45.0 <= rsi <= 65.0:
        score += 8.0

    elif 35.0 <= rsi < 45.0:
        score += 3.0

    elif rsi < 30.0:
        score += 2.0

    elif rsi >= 75.0:
        score -= 10.0

    elif rsi >= 68.0:
        score -= 4.0

    # MACD
    if macd > macd_signal:
        score += 8.0

    else:
        score -= 7.0

    if macd_hist > 0:
        score += 5.0

    else:
        score -= 4.0

    # Bollinger Band 위치
    if bb_lower < close < bb_upper:
        score += 3.0

    if close >= bb_upper:
        score -= 6.0

    if close <= bb_lower:
        score += 2.0

    # 거래량 확인
    if (
        volume_ma20 > 0
        and volume > volume_ma20
    ):
        score += 4.0

    return round(
        max(
            0.0,
            min(
                100.0,
                score,
            ),
        ),
        2,
    )


def score_to_signal(
    score: float,
) -> str:
    """
    점수를 추천 신호로 변환합니다.
    """

    if score >= 82.0:
        return "STRONG_BUY"

    if score >= 68.0:
        return "BUY"

    if score >= 55.0:
        return "WATCH_BUY"

    if score >= 42.0:
        return "HOLD"

    return "AVOID"


def calculate_maximum_drawdown(
    equity_values: list[float],
) -> float:
    """
    자산곡선에서 최대 낙폭을 계산합니다.
    """

    if not equity_values:
        return 0.0

    equity_series = pd.Series(
        equity_values,
        dtype=float,
    )

    running_peak = (
        equity_series.cummax()
    )

    drawdown = (
        (
            equity_series
            - running_peak
        )
        / running_peak.replace(
            0.0,
            np.nan,
        )
    ) * 100.0

    return round(
        safe_float(
            drawdown.min()
        ),
        2,
    )


def calculate_sharpe_ratio(
    daily_equity_values: list[float],
) -> float:
    """
    일별 자산 변화율을 이용해
    연환산 Sharpe Ratio를 계산합니다.

    무위험 수익률은 단순화를 위해 0으로 둡니다.
    """

    if len(
        daily_equity_values
    ) < 3:
        return 0.0

    equity_series = pd.Series(
        daily_equity_values,
        dtype=float,
    )

    daily_returns = (
        equity_series
        .pct_change()
        .dropna()
    )

    if daily_returns.empty:
        return 0.0

    standard_deviation = (
        daily_returns.std()
    )

    if (
        standard_deviation is None
        or standard_deviation == 0
        or np.isnan(
            standard_deviation
        )
    ):
        return 0.0

    sharpe = (
        daily_returns.mean()
        / standard_deviation
    ) * np.sqrt(
        252
    )

    return round(
        safe_float(
            sharpe
        ),
        2,
    )


def create_failed_result(
    symbol: str,
    initial_cash: float,
    settings: dict[str, Any],
    started_at: datetime,
    error: Exception,
) -> StrategyBacktestResult:
    """
    백테스트 실패 결과를 생성합니다.
    """

    finished_at = datetime.now()

    return StrategyBacktestResult(
        symbol=symbol,
        success=False,

        started_at=(
            started_at.isoformat()
        ),

        finished_at=(
            finished_at.isoformat()
        ),

        data_start_date=None,
        data_end_date=None,

        initial_cash=round(
            initial_cash,
            2,
        ),

        final_value=round(
            initial_cash,
            2,
        ),

        total_return_percent=0.0,
        buy_hold_return_percent=0.0,

        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        win_rate_percent=0.0,

        average_trade_return_percent=0.0,
        average_win_percent=0.0,
        average_loss_percent=0.0,

        best_trade_percent=0.0,
        worst_trade_percent=0.0,

        maximum_drawdown_percent=0.0,
        sharpe_ratio=0.0,
        profit_factor=0.0,

        average_holding_days=0.0,

        trades=[],
        equity_curve=[],

        settings=settings,

        error_type=(
            type(error).__name__
        ),

        error_message=str(
            error
        ),
    )


def run_recommendation_backtest(
    symbol: str,
    period: str = "10y",
    interval: str = "1d",
    initial_cash: float = 10_000.0,
    position_percent: float = 20.0,
    entry_score: float = 68.0,
    exit_score: float = 42.0,
    stop_atr_multiple: float = 1.5,
    target_atr_multiple: float = 3.0,
    maximum_holding_days: int = 20,
    commission_per_trade: float = 0.0,
) -> StrategyBacktestResult:
    """
    기술지표 추천 점수를 이용한
    V7.0 과거 전략 백테스트입니다.

    매수:
    전날 종가 기준 점수가 entry_score 이상이면
    다음 거래일 시가에 매수합니다.

    매도:
    손절가, 목표가, 최대 보유기간 또는
    exit_score 미만 신호 발생 시 매도합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    started_at = datetime.now()

    settings = {
        "period": period,
        "interval": interval,
        "initial_cash": initial_cash,
        "position_percent": position_percent,
        "entry_score": entry_score,
        "exit_score": exit_score,
        "stop_atr_multiple": stop_atr_multiple,
        "target_atr_multiple": target_atr_multiple,
        "maximum_holding_days": maximum_holding_days,
        "commission_per_trade": commission_per_trade,
    }

    try:
        if initial_cash <= 0:
            raise ValueError(
                "initial_cash는 0보다 커야 합니다."
            )

        if not 0 < position_percent <= 100:
            raise ValueError(
                "position_percent는 0 초과 "
                "100 이하여야 합니다."
            )

        if maximum_holding_days < 1:
            raise ValueError(
                "maximum_holding_days는 "
                "1 이상이어야 합니다."
            )

        raw_data = get_history(
            symbol=normalized_symbol,
            period=period,
            interval=interval,
        )

        data = prepare_backtest_data(
            raw_data
        )

        data["SCORE"] = data.apply(
            calculate_historical_score,
            axis=1,
        )

        data["SIGNAL"] = (
            data["SCORE"]
            .apply(
                score_to_signal
            )
        )

        cash = float(
            initial_cash
        )

        shares = 0

        entry_price = 0.0
        entry_date = None
        entry_score_value = 0.0
        entry_signal = ""

        stop_loss = 0.0
        target_price = 0.0

        holding_days = 0

        trades: list[
            BacktestTrade
        ] = []

        equity_curve: list[
            dict[str, Any]
        ] = []

        # 전일 신호로 다음날 시가에 진입하기 위해
        # 첫 번째 행은 건너뜁니다.
        for index_position in range(
            1,
            len(data),
        ):
            current_date = data.index[
                index_position
            ]

            current_row = data.iloc[
                index_position
            ]

            previous_row = data.iloc[
                index_position - 1
            ]

            current_open = safe_float(
                current_row["Open"]
            )

            current_high = safe_float(
                current_row["High"]
            )

            current_low = safe_float(
                current_row["Low"]
            )

            current_close = safe_float(
                current_row["Close"]
            )

            previous_score = safe_float(
                previous_row["SCORE"]
            )

            previous_signal = str(
                previous_row["SIGNAL"]
            )

            previous_atr = safe_float(
                previous_row["ATR14"]
            )

            exit_reason = None
            exit_price = None

            if shares > 0:
                holding_days += 1

                # 같은 날 손절가와 목표가에 모두 닿으면
                # 보수적으로 손절이 먼저 체결된 것으로 계산합니다.
                if current_low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "STOP_LOSS"

                elif current_high >= target_price:
                    exit_price = target_price
                    exit_reason = "TARGET"

                elif previous_score < exit_score:
                    exit_price = current_open
                    exit_reason = "EXIT_SIGNAL"

                elif (
                    holding_days
                    >= maximum_holding_days
                ):
                    exit_price = current_open
                    exit_reason = "MAX_HOLDING"

                if (
                    exit_reason is not None
                    and exit_price is not None
                ):
                    gross_exit_amount = (
                        shares
                        * exit_price
                    )

                    cash += (
                        gross_exit_amount
                        - commission_per_trade
                    )

                    invested_amount = (
                        shares
                        * entry_price
                    )

                    total_commission = (
                        commission_per_trade
                        * 2.0
                    )

                    profit_loss = (
                        (
                            exit_price
                            - entry_price
                        )
                        * shares
                        - total_commission
                    )

                    return_percent = (
                        profit_loss
                        / invested_amount
                    ) * 100.0

                    trade = BacktestTrade(
                        symbol=normalized_symbol,

                        entry_date=(
                            pd.Timestamp(
                                entry_date
                            )
                            .strftime(
                                "%Y-%m-%d"
                            )
                        ),

                        exit_date=(
                            pd.Timestamp(
                                current_date
                            )
                            .strftime(
                                "%Y-%m-%d"
                            )
                        ),

                        entry_price=round(
                            entry_price,
                            2,
                        ),

                        exit_price=round(
                            exit_price,
                            2,
                        ),

                        shares=shares,

                        entry_score=round(
                            entry_score_value,
                            2,
                        ),

                        entry_signal=entry_signal,

                        stop_loss=round(
                            stop_loss,
                            2,
                        ),

                        target_price=round(
                            target_price,
                            2,
                        ),

                        exit_reason=exit_reason,

                        invested_amount=round(
                            invested_amount,
                            2,
                        ),

                        profit_loss=round(
                            profit_loss,
                            2,
                        ),

                        return_percent=round(
                            return_percent,
                            2,
                        ),

                        holding_days=holding_days,
                    )

                    trades.append(
                        trade
                    )

                    shares = 0
                    entry_price = 0.0
                    entry_date = None
                    entry_score_value = 0.0
                    entry_signal = ""

                    stop_loss = 0.0
                    target_price = 0.0
                    holding_days = 0

            # 청산 이후 또는 미보유 상태에서 신규 진입
            if (
                shares == 0
                and previous_score >= entry_score
                and previous_atr > 0
                and current_open > 0
            ):
                investment_budget = (
                    cash
                    * (
                        position_percent
                        / 100.0
                    )
                )

                available_after_commission = max(
                    0.0,
                    investment_budget
                    - commission_per_trade,
                )

                calculated_shares = int(
                    available_after_commission
                    // current_open
                )

                total_entry_cost = (
                    calculated_shares
                    * current_open
                    + commission_per_trade
                )

                if (
                    calculated_shares > 0
                    and total_entry_cost <= cash
                ):
                    shares = calculated_shares

                    cash -= total_entry_cost

                    entry_price = current_open
                    entry_date = current_date

                    entry_score_value = (
                        previous_score
                    )

                    entry_signal = (
                        previous_signal
                    )

                    stop_loss = max(
                        0.01,
                        entry_price
                        - (
                            previous_atr
                            * stop_atr_multiple
                        ),
                    )

                    target_price = (
                        entry_price
                        + (
                            previous_atr
                            * target_atr_multiple
                        )
                    )

                    holding_days = 0

            current_equity = (
                cash
                + (
                    shares
                    * current_close
                )
            )

            equity_curve.append(
                {
                    "date": (
                        pd.Timestamp(
                            current_date
                        )
                        .strftime(
                            "%Y-%m-%d"
                        )
                    ),

                    "cash": round(
                        cash,
                        2,
                    ),

                    "shares": shares,

                    "close": round(
                        current_close,
                        2,
                    ),

                    "equity": round(
                        current_equity,
                        2,
                    ),
                }
            )

        # 마지막 날까지 보유 중이면 종가 청산
        if shares > 0:
            final_date = data.index[-1]

            final_close = safe_float(
                data.iloc[-1]["Close"]
            )

            cash += (
                shares
                * final_close
                - commission_per_trade
            )

            invested_amount = (
                shares
                * entry_price
            )

            total_commission = (
                commission_per_trade
                * 2.0
            )

            profit_loss = (
                (
                    final_close
                    - entry_price
                )
                * shares
                - total_commission
            )

            return_percent = (
                profit_loss
                / invested_amount
            ) * 100.0

            trades.append(
                BacktestTrade(
                    symbol=normalized_symbol,

                    entry_date=(
                        pd.Timestamp(
                            entry_date
                        )
                        .strftime(
                            "%Y-%m-%d"
                        )
                    ),

                    exit_date=(
                        pd.Timestamp(
                            final_date
                        )
                        .strftime(
                            "%Y-%m-%d"
                        )
                    ),

                    entry_price=round(
                        entry_price,
                        2,
                    ),

                    exit_price=round(
                        final_close,
                        2,
                    ),

                    shares=shares,

                    entry_score=round(
                        entry_score_value,
                        2,
                    ),

                    entry_signal=entry_signal,

                    stop_loss=round(
                        stop_loss,
                        2,
                    ),

                    target_price=round(
                        target_price,
                        2,
                    ),

                    exit_reason="END_OF_DATA",

                    invested_amount=round(
                        invested_amount,
                        2,
                    ),

                    profit_loss=round(
                        profit_loss,
                        2,
                    ),

                    return_percent=round(
                        return_percent,
                        2,
                    ),

                    holding_days=holding_days,
                )
            )

            if equity_curve:
                equity_curve[-1][
                    "cash"
                ] = round(
                    cash,
                    2,
                )

                equity_curve[-1][
                    "shares"
                ] = 0

                equity_curve[-1][
                    "equity"
                ] = round(
                    cash,
                    2,
                )

        final_value = cash

        total_return_percent = (
            (
                final_value
                - initial_cash
            )
            / initial_cash
        ) * 100.0

        first_close = safe_float(
            data.iloc[0]["Close"]
        )

        last_close = safe_float(
            data.iloc[-1]["Close"]
        )

        buy_hold_return_percent = (
            (
                last_close
                - first_close
            )
            / first_close
        ) * 100.0

        trade_returns = [
            trade.return_percent
            for trade in trades
        ]

        winning_returns = [
            value
            for value in trade_returns
            if value > 0
        ]

        losing_returns = [
            value
            for value in trade_returns
            if value <= 0
        ]

        winning_trades = len(
            winning_returns
        )

        losing_trades = len(
            losing_returns
        )

        total_trades = len(
            trades
        )

        if total_trades > 0:
            win_rate_percent = (
                winning_trades
                / total_trades
            ) * 100.0

            average_trade_return = float(
                np.mean(
                    trade_returns
                )
            )

            average_holding_days = float(
                np.mean(
                    [
                        trade.holding_days
                        for trade in trades
                    ]
                )
            )

            best_trade_percent = max(
                trade_returns
            )

            worst_trade_percent = min(
                trade_returns
            )

        else:
            win_rate_percent = 0.0
            average_trade_return = 0.0
            average_holding_days = 0.0
            best_trade_percent = 0.0
            worst_trade_percent = 0.0

        average_win_percent = (
            float(
                np.mean(
                    winning_returns
                )
            )
            if winning_returns
            else 0.0
        )

        average_loss_percent = (
            float(
                np.mean(
                    losing_returns
                )
            )
            if losing_returns
            else 0.0
        )

        gross_profit = sum(
            max(
                trade.profit_loss,
                0.0,
            )
            for trade in trades
        )

        gross_loss = abs(
            sum(
                min(
                    trade.profit_loss,
                    0.0,
                )
                for trade in trades
            )
        )

        if gross_loss > 0:
            profit_factor = (
                gross_profit
                / gross_loss
            )

        elif gross_profit > 0:
            profit_factor = float(
                "inf"
            )

        else:
            profit_factor = 0.0

        equity_values = [
            safe_float(
                item["equity"]
            )
            for item in equity_curve
        ]

        maximum_drawdown = (
            calculate_maximum_drawdown(
                equity_values
            )
        )

        sharpe_ratio = (
            calculate_sharpe_ratio(
                equity_values
            )
        )

        finished_at = datetime.now()

        return StrategyBacktestResult(
            symbol=normalized_symbol,
            success=True,

            started_at=(
                started_at.isoformat()
            ),

            finished_at=(
                finished_at.isoformat()
            ),

            data_start_date=(
                pd.Timestamp(
                    data.index[0]
                )
                .strftime(
                    "%Y-%m-%d"
                )
            ),

            data_end_date=(
                pd.Timestamp(
                    data.index[-1]
                )
                .strftime(
                    "%Y-%m-%d"
                )
            ),

            initial_cash=round(
                initial_cash,
                2,
            ),

            final_value=round(
                final_value,
                2,
            ),

            total_return_percent=round(
                total_return_percent,
                2,
            ),

            buy_hold_return_percent=round(
                buy_hold_return_percent,
                2,
            ),

            total_trades=total_trades,

            winning_trades=winning_trades,
            losing_trades=losing_trades,

            win_rate_percent=round(
                win_rate_percent,
                2,
            ),

            average_trade_return_percent=round(
                average_trade_return,
                2,
            ),

            average_win_percent=round(
                average_win_percent,
                2,
            ),

            average_loss_percent=round(
                average_loss_percent,
                2,
            ),

            best_trade_percent=round(
                best_trade_percent,
                2,
            ),

            worst_trade_percent=round(
                worst_trade_percent,
                2,
            ),

            maximum_drawdown_percent=round(
                maximum_drawdown,
                2,
            ),

            sharpe_ratio=round(
                sharpe_ratio,
                2,
            ),

            profit_factor=round(
                profit_factor,
                2,
            ),

            average_holding_days=round(
                average_holding_days,
                2,
            ),

            trades=[
                trade.to_dict()
                for trade in trades
            ],

            equity_curve=equity_curve,

            settings=settings,
        )

    except Exception as error:
        return create_failed_result(
            symbol=normalized_symbol,
            initial_cash=initial_cash,
            settings=settings,
            started_at=started_at,
            error=error,
        )


def save_backtest_result(
    result: StrategyBacktestResult,
) -> tuple[Path, Path]:
    """
    종목별 백테스트 결과를 JSON으로 저장합니다.
    """

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    report_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_strategy_backtest_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_strategy_backtest_"
            "latest.json"
        )
    )

    result_data = result.to_dict()

    for path in (
        report_path,
        latest_path,
    ):
        with path.open(
            mode="w",
            encoding="utf-8",
        ) as file:
            json.dump(
                result_data,
                file,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

    return (
        report_path,
        latest_path,
    )


def print_backtest_result(
    result: StrategyBacktestResult,
) -> None:
    """
    백테스트 핵심 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 76)
    print(
        f"{result.symbol} V7.0 "
        "RECOMMENDATION STRATEGY BACKTEST"
    )
    print("=" * 76)

    if not result.success:
        print(
            "Status                : FAILED"
        )

        print(
            f"Error type            : "
            f"{result.error_type}"
        )

        print(
            f"Error message         : "
            f"{result.error_message}"
        )

        print("=" * 76)
        return

    print(
        f"Period                : "
        f"{result.data_start_date} "
        f"to {result.data_end_date}"
    )

    print(
        f"Initial cash          : "
        f"${result.initial_cash:,.2f}"
    )

    print(
        f"Final value           : "
        f"${result.final_value:,.2f}"
    )

    print(
        f"Strategy return       : "
        f"{result.total_return_percent:.2f}%"
    )

    print(
        f"Buy and hold return   : "
        f"{result.buy_hold_return_percent:.2f}%"
    )

    print()
    print(
        f"Total trades          : "
        f"{result.total_trades}"
    )

    print(
        f"Winning trades        : "
        f"{result.winning_trades}"
    )

    print(
        f"Losing trades         : "
        f"{result.losing_trades}"
    )

    print(
        f"Win rate              : "
        f"{result.win_rate_percent:.2f}%"
    )

    print(
        f"Average trade return  : "
        f"{result.average_trade_return_percent:.2f}%"
    )

    print(
        f"Average win           : "
        f"{result.average_win_percent:.2f}%"
    )

    print(
        f"Average loss          : "
        f"{result.average_loss_percent:.2f}%"
    )

    print(
        f"Best trade            : "
        f"{result.best_trade_percent:.2f}%"
    )

    print(
        f"Worst trade           : "
        f"{result.worst_trade_percent:.2f}%"
    )

    print()
    print(
        f"Maximum drawdown      : "
        f"{result.maximum_drawdown_percent:.2f}%"
    )

    print(
        f"Sharpe ratio          : "
        f"{result.sharpe_ratio:.2f}"
    )

    if np.isinf(
        result.profit_factor
    ):
        profit_factor_text = "INF"

    else:
        profit_factor_text = (
            f"{result.profit_factor:.2f}"
        )

    print(
        f"Profit factor         : "
        f"{profit_factor_text}"
    )

    print(
        f"Average holding days  : "
        f"{result.average_holding_days:.2f}"
    )

    print("=" * 76)

    print(
        "주의: 이 결과는 과거 가격을 이용한 "
        "기술적 전략 테스트이며 미래 수익을 보장하지 않습니다."
    )