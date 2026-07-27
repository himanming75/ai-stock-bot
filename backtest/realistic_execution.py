import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtest.recommendation_backtester import (
    calculate_historical_score,
    calculate_maximum_drawdown,
    calculate_sharpe_ratio,
    normalize_symbol,
    prepare_backtest_data,
    safe_float,
    score_to_signal,
)
from data.market import get_history


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "realistic_execution"
)


@dataclass
class RealisticTrade:
    """
    실제 체결 조건을 반영한 한 번의 완결된 거래입니다.

    market_entry_price:
        슬리피지 적용 전 시장 진입 기준 가격

    entry_fill_price:
        슬리피지 적용 후 실제 매수 체결 가격

    market_exit_price:
        슬리피지 적용 전 시장 청산 기준 가격

    exit_fill_price:
        슬리피지 적용 후 실제 매도 체결 가격
    """

    symbol: str

    entry_date: str
    exit_date: str

    market_entry_price: float
    entry_fill_price: float

    market_exit_price: float
    exit_fill_price: float

    shares: int

    entry_score: float
    entry_signal: str

    stop_loss: float
    target_price: float

    exit_reason: str
    holding_days: int

    gross_entry_value: float
    gross_exit_value: float

    entry_commission: float
    exit_commission: float
    total_commission: float

    entry_slippage_cost: float
    exit_slippage_cost: float
    total_slippage_cost: float

    total_execution_cost: float

    net_invested_amount: float
    net_exit_proceeds: float

    gross_profit_loss: float
    net_profit_loss: float

    gross_return_percent: float
    net_return_percent: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RealisticExecutionResult:
    """
    현실적인 체결 비용을 반영한 백테스트 결과입니다.
    """

    version: str

    symbol: str
    success: bool

    started_at: str
    finished_at: str
    elapsed_seconds: float

    data_start_date: str | None
    data_end_date: str | None
    total_rows: int

    initial_cash: float
    final_value: float

    gross_baseline_final_value: float
    gross_baseline_return_percent: float

    net_return_percent: float
    buy_hold_return_percent: float
    excess_return_percent: float

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

    total_commission_cost: float
    total_slippage_cost: float
    total_execution_cost: float

    execution_cost_percent_of_initial_cash: float
    return_reduction_percent: float

    average_cost_per_trade: float
    average_slippage_cost_per_trade: float
    average_commission_per_trade: float

    settings: dict[str, Any]

    trades: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]

    error_type: str | None = None
    error_message: str | None = None

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_execution_settings(
    initial_cash: float,
    position_percent: float,
    entry_score: float,
    exit_score: float,
    stop_atr_multiple: float,
    target_atr_multiple: float,
    maximum_holding_days: int,
    commission_per_order: float,
    slippage_percent: float,
) -> None:
    """
    실행 설정값을 검사합니다.
    """

    if initial_cash <= 0:
        raise ValueError(
            "initial_cash는 0보다 커야 합니다."
        )

    if not 0 < position_percent <= 100:
        raise ValueError(
            "position_percent는 0 초과 "
            "100 이하여야 합니다."
        )

    if entry_score < 0 or entry_score > 100:
        raise ValueError(
            "entry_score는 0 이상 100 이하여야 합니다."
        )

    if exit_score < 0 or exit_score > 100:
        raise ValueError(
            "exit_score는 0 이상 100 이하여야 합니다."
        )

    if exit_score >= entry_score:
        raise ValueError(
            "exit_score는 entry_score보다 낮아야 합니다."
        )

    if stop_atr_multiple <= 0:
        raise ValueError(
            "stop_atr_multiple은 0보다 커야 합니다."
        )

    if target_atr_multiple <= 0:
        raise ValueError(
            "target_atr_multiple은 0보다 커야 합니다."
        )

    if maximum_holding_days < 1:
        raise ValueError(
            "maximum_holding_days는 1 이상이어야 합니다."
        )

    if commission_per_order < 0:
        raise ValueError(
            "commission_per_order는 0 이상이어야 합니다."
        )

    if slippage_percent < 0:
        raise ValueError(
            "slippage_percent는 0 이상이어야 합니다."
        )

    if slippage_percent >= 10:
        raise ValueError(
            "slippage_percent가 비정상적으로 큽니다. "
            "0.05는 0.05%를 의미합니다."
        )


def calculate_buy_fill_price(
    market_price: float,
    slippage_percent: float,
) -> float:
    """
    매수 체결 가격을 계산합니다.

    매수자는 시장 기준 가격보다 불리하게
    조금 높은 가격에 체결되는 것으로 계산합니다.
    """

    if market_price <= 0:
        raise ValueError(
            "매수 시장 가격은 0보다 커야 합니다."
        )

    fill_price = market_price * (
        1.0
        + slippage_percent / 100.0
    )

    return float(fill_price)


def calculate_sell_fill_price(
    market_price: float,
    slippage_percent: float,
) -> float:
    """
    매도 체결 가격을 계산합니다.

    매도자는 시장 기준 가격보다 불리하게
    조금 낮은 가격에 체결되는 것으로 계산합니다.
    """

    if market_price <= 0:
        raise ValueError(
            "매도 시장 가격은 0보다 커야 합니다."
        )

    fill_price = market_price * (
        1.0
        - slippage_percent / 100.0
    )

    return max(
        float(fill_price),
        0.01,
    )


def calculate_profit_factor(
    trades: list[RealisticTrade],
) -> float:
    """
    실제 순손익을 이용해 Profit Factor를 계산합니다.
    """

    gross_profit = sum(
        max(
            trade.net_profit_loss,
            0.0,
        )
        for trade in trades
    )

    gross_loss = abs(
        sum(
            min(
                trade.net_profit_loss,
                0.0,
            )
            for trade in trades
        )
    )

    if gross_loss > 0:
        return round(
            gross_profit / gross_loss,
            2,
        )

    if gross_profit > 0:
        return float("inf")

    return 0.0


def create_failed_realistic_result(
    symbol: str,
    initial_cash: float,
    settings: dict[str, Any],
    started_at: datetime,
    error: Exception,
) -> RealisticExecutionResult:
    """
    실행 실패 결과를 생성합니다.
    """

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    return RealisticExecutionResult(
        version="V7.8",

        symbol=symbol,
        success=False,

        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        elapsed_seconds=round(
            elapsed_seconds,
            2,
        ),

        data_start_date=None,
        data_end_date=None,
        total_rows=0,

        initial_cash=round(
            initial_cash,
            2,
        ),

        final_value=round(
            initial_cash,
            2,
        ),

        gross_baseline_final_value=round(
            initial_cash,
            2,
        ),

        gross_baseline_return_percent=0.0,

        net_return_percent=0.0,
        buy_hold_return_percent=0.0,
        excess_return_percent=0.0,

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

        total_commission_cost=0.0,
        total_slippage_cost=0.0,
        total_execution_cost=0.0,

        execution_cost_percent_of_initial_cash=0.0,
        return_reduction_percent=0.0,

        average_cost_per_trade=0.0,
        average_slippage_cost_per_trade=0.0,
        average_commission_per_trade=0.0,

        settings=settings,

        trades=[],
        equity_curve=[],

        error_type=type(error).__name__,
        error_message=str(error),
    )


def run_realistic_execution_backtest(
    symbol: str,

    period: str = "10y",
    interval: str = "1d",

    initial_cash: float = 10_000.0,
    position_percent: float = 20.0,

    entry_score: float = 62.0,
    exit_score: float = 44.0,

    stop_atr_multiple: float = 1.50,
    target_atr_multiple: float = 2.25,

    maximum_holding_days: int = 20,

    commission_per_order: float = 0.0,
    slippage_percent: float = 0.05,
) -> RealisticExecutionResult:
    """
    실제 체결가, 수수료, 슬리피지를 반영한 백테스트입니다.

    진입 규칙:
        전일 SCORE가 entry_score 이상이면
        다음 거래일 시가를 기준으로 매수합니다.

    매수 체결가:
        다음 거래일 시가 × (1 + slippage)

    청산 규칙:
        손절가
        목표가
        전일 점수 하락
        최대 보유기간
        데이터 마지막 날

    매도 체결가:
        시장 청산 기준 가격 × (1 - slippage)

    주의:
        Stop과 Target이 같은 날 모두 닿으면
        기존 백테스트와 동일하게 Stop이 먼저
        체결된 것으로 보수적으로 계산합니다.
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

        "stop_atr_multiple": (
            stop_atr_multiple
        ),

        "target_atr_multiple": (
            target_atr_multiple
        ),

        "maximum_holding_days": (
            maximum_holding_days
        ),

        "commission_per_order": (
            commission_per_order
        ),

        "slippage_percent": (
            slippage_percent
        ),

        "same_day_stop_target_rule": (
            "STOP_FIRST"
        ),

        "entry_timing": (
            "PREVIOUS_SIGNAL_NEXT_OPEN"
        ),
    }

    try:
        validate_execution_settings(
            initial_cash=initial_cash,
            position_percent=position_percent,

            entry_score=entry_score,
            exit_score=exit_score,

            stop_atr_multiple=(
                stop_atr_multiple
            ),

            target_atr_multiple=(
                target_atr_multiple
            ),

            maximum_holding_days=(
                maximum_holding_days
            ),

            commission_per_order=(
                commission_per_order
            ),

            slippage_percent=(
                slippage_percent
            ),
        )

        print()
        print("=" * 118)
        print(
            f"{normalized_symbol} V7.8 "
            "REALISTIC EXECUTION BACKTEST"
        )
        print("=" * 118)

        print(
            "Downloading complete market data..."
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

        print(
            f"Full period              : "
            f"{pd.Timestamp(data.index[0]).strftime('%Y-%m-%d')} "
            f"to "
            f"{pd.Timestamp(data.index[-1]).strftime('%Y-%m-%d')}"
        )

        print(
            f"Rows                     : "
            f"{len(data)}"
        )

        print(
            f"Entry / Exit score       : "
            f"{entry_score:.0f} / "
            f"{exit_score:.0f}"
        )

        print(
            f"Stop / Target ATR        : "
            f"{stop_atr_multiple:.2f} / "
            f"{target_atr_multiple:.2f}"
        )

        print(
            f"Commission per order     : "
            f"${commission_per_order:.2f}"
        )

        print(
            f"Slippage per order       : "
            f"{slippage_percent:.3f}%"
        )

        print("=" * 118)

        cash = float(
            initial_cash
        )

        shares = 0

        entry_date: pd.Timestamp | None = None

        market_entry_price = 0.0
        entry_fill_price = 0.0

        entry_score_value = 0.0
        entry_signal = ""

        stop_loss = 0.0
        target_price = 0.0

        holding_days = 0

        current_entry_commission = 0.0
        current_entry_slippage_cost = 0.0

        trades: list[
            RealisticTrade
        ] = []

        equity_curve: list[
            dict[str, Any]
        ] = []

        total_commission_cost = 0.0
        total_slippage_cost = 0.0

        # 비용이 없었을 때의 비교용 자산입니다.
        gross_baseline_cash = float(
            initial_cash
        )

        gross_baseline_shares = 0
        gross_baseline_entry_price = 0.0

        for index_position in range(
            1,
            len(data),
        ):
            current_date = pd.Timestamp(
                data.index[index_position]
            )

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

            # -------------------------------------------------
            # 1. 기존 보유 포지션의 청산 조건 확인
            # -------------------------------------------------
            market_exit_price: float | None = None
            exit_reason: str | None = None

            if shares > 0:
                holding_days += 1

                if current_low <= stop_loss:
                    market_exit_price = stop_loss
                    exit_reason = "STOP_LOSS"

                elif current_high >= target_price:
                    market_exit_price = target_price
                    exit_reason = "TARGET"

                elif previous_score < exit_score:
                    market_exit_price = current_open
                    exit_reason = "EXIT_SIGNAL"

                elif (
                    holding_days
                    >= maximum_holding_days
                ):
                    market_exit_price = current_open
                    exit_reason = "MAX_HOLDING"

            if (
                shares > 0
                and market_exit_price is not None
                and exit_reason is not None
            ):
                exit_fill_price = (
                    calculate_sell_fill_price(
                        market_price=market_exit_price,
                        slippage_percent=(
                            slippage_percent
                        ),
                    )
                )

                gross_exit_value = (
                    shares
                    * market_exit_price
                )

                actual_exit_value = (
                    shares
                    * exit_fill_price
                )

                exit_slippage_cost = max(
                    0.0,
                    gross_exit_value
                    - actual_exit_value,
                )

                exit_commission = (
                    commission_per_order
                )

                net_exit_proceeds = (
                    actual_exit_value
                    - exit_commission
                )

                cash += net_exit_proceeds

                total_commission_cost += (
                    exit_commission
                )

                total_slippage_cost += (
                    exit_slippage_cost
                )

                gross_entry_value = (
                    shares
                    * market_entry_price
                )

                actual_entry_value = (
                    shares
                    * entry_fill_price
                )

                net_invested_amount = (
                    actual_entry_value
                    + current_entry_commission
                )

                total_commission = (
                    current_entry_commission
                    + exit_commission
                )

                total_slippage = (
                    current_entry_slippage_cost
                    + exit_slippage_cost
                )

                total_execution_cost = (
                    total_commission
                    + total_slippage
                )

                gross_profit_loss = (
                    gross_exit_value
                    - gross_entry_value
                )

                net_profit_loss = (
                    net_exit_proceeds
                    - net_invested_amount
                )

                gross_return_percent = (
                    (
                        gross_profit_loss
                        / gross_entry_value
                    )
                    * 100.0
                    if gross_entry_value > 0
                    else 0.0
                )

                net_return_percent = (
                    (
                        net_profit_loss
                        / net_invested_amount
                    )
                    * 100.0
                    if net_invested_amount > 0
                    else 0.0
                )

                trade = RealisticTrade(
                    symbol=normalized_symbol,

                    entry_date=(
                        pd.Timestamp(
                            entry_date
                        ).strftime(
                            "%Y-%m-%d"
                        )
                    ),

                    exit_date=(
                        current_date.strftime(
                            "%Y-%m-%d"
                        )
                    ),

                    market_entry_price=round(
                        market_entry_price,
                        4,
                    ),

                    entry_fill_price=round(
                        entry_fill_price,
                        4,
                    ),

                    market_exit_price=round(
                        market_exit_price,
                        4,
                    ),

                    exit_fill_price=round(
                        exit_fill_price,
                        4,
                    ),

                    shares=shares,

                    entry_score=round(
                        entry_score_value,
                        2,
                    ),

                    entry_signal=entry_signal,

                    stop_loss=round(
                        stop_loss,
                        4,
                    ),

                    target_price=round(
                        target_price,
                        4,
                    ),

                    exit_reason=exit_reason,
                    holding_days=holding_days,

                    gross_entry_value=round(
                        gross_entry_value,
                        2,
                    ),

                    gross_exit_value=round(
                        gross_exit_value,
                        2,
                    ),

                    entry_commission=round(
                        current_entry_commission,
                        2,
                    ),

                    exit_commission=round(
                        exit_commission,
                        2,
                    ),

                    total_commission=round(
                        total_commission,
                        2,
                    ),

                    entry_slippage_cost=round(
                        current_entry_slippage_cost,
                        2,
                    ),

                    exit_slippage_cost=round(
                        exit_slippage_cost,
                        2,
                    ),

                    total_slippage_cost=round(
                        total_slippage,
                        2,
                    ),

                    total_execution_cost=round(
                        total_execution_cost,
                        2,
                    ),

                    net_invested_amount=round(
                        net_invested_amount,
                        2,
                    ),

                    net_exit_proceeds=round(
                        net_exit_proceeds,
                        2,
                    ),

                    gross_profit_loss=round(
                        gross_profit_loss,
                        2,
                    ),

                    net_profit_loss=round(
                        net_profit_loss,
                        2,
                    ),

                    gross_return_percent=round(
                        gross_return_percent,
                        2,
                    ),

                    net_return_percent=round(
                        net_return_percent,
                        2,
                    ),
                )

                trades.append(
                    trade
                )

                # 비용 없는 비교 포지션 청산
                if gross_baseline_shares > 0:
                    gross_baseline_cash += (
                        gross_baseline_shares
                        * market_exit_price
                    )

                    gross_baseline_shares = 0
                    gross_baseline_entry_price = 0.0

                shares = 0

                entry_date = None

                market_entry_price = 0.0
                entry_fill_price = 0.0

                entry_score_value = 0.0
                entry_signal = ""

                stop_loss = 0.0
                target_price = 0.0

                holding_days = 0

                current_entry_commission = 0.0
                current_entry_slippage_cost = 0.0

            # -------------------------------------------------
            # 2. 신규 진입
            # -------------------------------------------------
            if (
                shares == 0
                and previous_score >= entry_score
                and previous_atr > 0
                and current_open > 0
            ):
                market_buy_price = (
                    current_open
                )

                buy_fill_price = (
                    calculate_buy_fill_price(
                        market_price=(
                            market_buy_price
                        ),

                        slippage_percent=(
                            slippage_percent
                        ),
                    )
                )

                investment_budget = (
                    cash
                    * position_percent
                    / 100.0
                )

                available_for_shares = max(
                    0.0,
                    investment_budget
                    - commission_per_order,
                )

                calculated_shares = int(
                    available_for_shares
                    // buy_fill_price
                )

                actual_entry_value = (
                    calculated_shares
                    * buy_fill_price
                )

                entry_commission = (
                    commission_per_order
                )

                total_entry_cash_required = (
                    actual_entry_value
                    + entry_commission
                )

                if (
                    calculated_shares > 0
                    and total_entry_cash_required
                    <= cash
                ):
                    shares = calculated_shares

                    cash -= (
                        total_entry_cash_required
                    )

                    entry_date = current_date

                    market_entry_price = (
                        market_buy_price
                    )

                    entry_fill_price = (
                        buy_fill_price
                    )

                    entry_score_value = (
                        previous_score
                    )

                    entry_signal = (
                        previous_signal
                    )

                    current_entry_commission = (
                        entry_commission
                    )

                    current_entry_slippage_cost = (
                        (
                            entry_fill_price
                            - market_entry_price
                        )
                        * shares
                    )

                    total_commission_cost += (
                        current_entry_commission
                    )

                    total_slippage_cost += (
                        current_entry_slippage_cost
                    )

                    # 실제 체결가를 기준으로 손절과 목표가 설정
                    stop_loss = max(
                        0.01,
                        entry_fill_price
                        - (
                            previous_atr
                            * stop_atr_multiple
                        ),
                    )

                    target_price = (
                        entry_fill_price
                        + (
                            previous_atr
                            * target_atr_multiple
                        )
                    )

                    holding_days = 0

                    # 비용 없는 비교 포지션
                    gross_budget = (
                        gross_baseline_cash
                        * position_percent
                        / 100.0
                    )

                    gross_calculated_shares = int(
                        gross_budget
                        // market_buy_price
                    )

                    gross_entry_cost = (
                        gross_calculated_shares
                        * market_buy_price
                    )

                    if (
                        gross_calculated_shares > 0
                        and gross_entry_cost
                        <= gross_baseline_cash
                    ):
                        gross_baseline_shares = (
                            gross_calculated_shares
                        )

                        gross_baseline_cash -= (
                            gross_entry_cost
                        )

                        gross_baseline_entry_price = (
                            market_buy_price
                        )

            # -------------------------------------------------
            # 3. 일별 실제 자산곡선 기록
            # -------------------------------------------------
            market_value = (
                shares
                * current_close
            )

            current_equity = (
                cash
                + market_value
            )

            gross_market_value = (
                gross_baseline_shares
                * current_close
            )

            gross_current_equity = (
                gross_baseline_cash
                + gross_market_value
            )

            equity_curve.append(
                {
                    "date": (
                        current_date.strftime(
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
                        4,
                    ),

                    "market_value": round(
                        market_value,
                        2,
                    ),

                    "equity": round(
                        current_equity,
                        2,
                    ),

                    "gross_baseline_equity": round(
                        gross_current_equity,
                        2,
                    ),

                    "cumulative_commission": round(
                        total_commission_cost,
                        2,
                    ),

                    "cumulative_slippage": round(
                        total_slippage_cost,
                        2,
                    ),

                    "cumulative_execution_cost": round(
                        total_commission_cost
                        + total_slippage_cost,
                        2,
                    ),
                }
            )

        # -----------------------------------------------------
        # 4. 마지막 날까지 포지션 보유 시 종가 청산
        # -----------------------------------------------------
        if shares > 0:
            final_date = pd.Timestamp(
                data.index[-1]
            )

            final_market_close = safe_float(
                data.iloc[-1]["Close"]
            )

            final_fill_price = (
                calculate_sell_fill_price(
                    market_price=(
                        final_market_close
                    ),

                    slippage_percent=(
                        slippage_percent
                    ),
                )
            )

            gross_exit_value = (
                shares
                * final_market_close
            )

            actual_exit_value = (
                shares
                * final_fill_price
            )

            exit_slippage_cost = max(
                0.0,
                gross_exit_value
                - actual_exit_value,
            )

            exit_commission = (
                commission_per_order
            )

            net_exit_proceeds = (
                actual_exit_value
                - exit_commission
            )

            cash += net_exit_proceeds

            total_commission_cost += (
                exit_commission
            )

            total_slippage_cost += (
                exit_slippage_cost
            )

            gross_entry_value = (
                shares
                * market_entry_price
            )

            actual_entry_value = (
                shares
                * entry_fill_price
            )

            net_invested_amount = (
                actual_entry_value
                + current_entry_commission
            )

            total_commission = (
                current_entry_commission
                + exit_commission
            )

            total_slippage = (
                current_entry_slippage_cost
                + exit_slippage_cost
            )

            total_execution_cost = (
                total_commission
                + total_slippage
            )

            gross_profit_loss = (
                gross_exit_value
                - gross_entry_value
            )

            net_profit_loss = (
                net_exit_proceeds
                - net_invested_amount
            )

            gross_return_percent = (
                (
                    gross_profit_loss
                    / gross_entry_value
                )
                * 100.0
                if gross_entry_value > 0
                else 0.0
            )

            net_return_percent = (
                (
                    net_profit_loss
                    / net_invested_amount
                )
                * 100.0
                if net_invested_amount > 0
                else 0.0
            )

            trades.append(
                RealisticTrade(
                    symbol=normalized_symbol,

                    entry_date=(
                        pd.Timestamp(
                            entry_date
                        ).strftime(
                            "%Y-%m-%d"
                        )
                    ),

                    exit_date=(
                        final_date.strftime(
                            "%Y-%m-%d"
                        )
                    ),

                    market_entry_price=round(
                        market_entry_price,
                        4,
                    ),

                    entry_fill_price=round(
                        entry_fill_price,
                        4,
                    ),

                    market_exit_price=round(
                        final_market_close,
                        4,
                    ),

                    exit_fill_price=round(
                        final_fill_price,
                        4,
                    ),

                    shares=shares,

                    entry_score=round(
                        entry_score_value,
                        2,
                    ),

                    entry_signal=entry_signal,

                    stop_loss=round(
                        stop_loss,
                        4,
                    ),

                    target_price=round(
                        target_price,
                        4,
                    ),

                    exit_reason="END_OF_DATA",
                    holding_days=holding_days,

                    gross_entry_value=round(
                        gross_entry_value,
                        2,
                    ),

                    gross_exit_value=round(
                        gross_exit_value,
                        2,
                    ),

                    entry_commission=round(
                        current_entry_commission,
                        2,
                    ),

                    exit_commission=round(
                        exit_commission,
                        2,
                    ),

                    total_commission=round(
                        total_commission,
                        2,
                    ),

                    entry_slippage_cost=round(
                        current_entry_slippage_cost,
                        2,
                    ),

                    exit_slippage_cost=round(
                        exit_slippage_cost,
                        2,
                    ),

                    total_slippage_cost=round(
                        total_slippage,
                        2,
                    ),

                    total_execution_cost=round(
                        total_execution_cost,
                        2,
                    ),

                    net_invested_amount=round(
                        net_invested_amount,
                        2,
                    ),

                    net_exit_proceeds=round(
                        net_exit_proceeds,
                        2,
                    ),

                    gross_profit_loss=round(
                        gross_profit_loss,
                        2,
                    ),

                    net_profit_loss=round(
                        net_profit_loss,
                        2,
                    ),

                    gross_return_percent=round(
                        gross_return_percent,
                        2,
                    ),

                    net_return_percent=round(
                        net_return_percent,
                        2,
                    ),
                )
            )

            if gross_baseline_shares > 0:
                gross_baseline_cash += (
                    gross_baseline_shares
                    * final_market_close
                )

                gross_baseline_shares = 0

            shares = 0

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
                    "market_value"
                ] = 0.0

                equity_curve[-1][
                    "equity"
                ] = round(
                    cash,
                    2,
                )

                equity_curve[-1][
                    "gross_baseline_equity"
                ] = round(
                    gross_baseline_cash,
                    2,
                )

                equity_curve[-1][
                    "cumulative_commission"
                ] = round(
                    total_commission_cost,
                    2,
                )

                equity_curve[-1][
                    "cumulative_slippage"
                ] = round(
                    total_slippage_cost,
                    2,
                )

                equity_curve[-1][
                    "cumulative_execution_cost"
                ] = round(
                    total_commission_cost
                    + total_slippage_cost,
                    2,
                )

        final_value = float(
            cash
        )

        gross_baseline_final_value = float(
            gross_baseline_cash
            + (
                gross_baseline_shares
                * safe_float(
                    data.iloc[-1]["Close"]
                )
            )
        )

        net_return_percent = (
            (
                final_value
                - initial_cash
            )
            / initial_cash
        ) * 100.0

        gross_baseline_return_percent = (
            (
                gross_baseline_final_value
                - initial_cash
            )
            / initial_cash
        ) * 100.0

        return_reduction_percent = (
            gross_baseline_return_percent
            - net_return_percent
        )

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

        excess_return_percent = (
            net_return_percent
            - buy_hold_return_percent
        )

        trade_returns = [
            trade.net_return_percent
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

        total_trades = len(
            trades
        )

        winning_trades = len(
            winning_returns
        )

        losing_trades = len(
            losing_returns
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

        profit_factor = (
            calculate_profit_factor(
                trades
            )
        )

        total_execution_cost = (
            total_commission_cost
            + total_slippage_cost
        )

        execution_cost_percent = (
            (
                total_execution_cost
                / initial_cash
            )
            * 100.0
            if initial_cash > 0
            else 0.0
        )

        average_cost_per_trade = (
            total_execution_cost
            / total_trades
            if total_trades > 0
            else 0.0
        )

        average_slippage_per_trade = (
            total_slippage_cost
            / total_trades
            if total_trades > 0
            else 0.0
        )

        average_commission_per_trade = (
            total_commission_cost
            / total_trades
            if total_trades > 0
            else 0.0
        )

        finished_at = datetime.now()

        elapsed_seconds = (
            finished_at
            - started_at
        ).total_seconds()

        return RealisticExecutionResult(
            version="V7.8",

            symbol=normalized_symbol,
            success=True,

            started_at=started_at.isoformat(),
            finished_at=finished_at.isoformat(),

            elapsed_seconds=round(
                elapsed_seconds,
                2,
            ),

            data_start_date=(
                pd.Timestamp(
                    data.index[0]
                ).strftime(
                    "%Y-%m-%d"
                )
            ),

            data_end_date=(
                pd.Timestamp(
                    data.index[-1]
                ).strftime(
                    "%Y-%m-%d"
                )
            ),

            total_rows=len(
                data
            ),

            initial_cash=round(
                initial_cash,
                2,
            ),

            final_value=round(
                final_value,
                2,
            ),

            gross_baseline_final_value=round(
                gross_baseline_final_value,
                2,
            ),

            gross_baseline_return_percent=round(
                gross_baseline_return_percent,
                2,
            ),

            net_return_percent=round(
                net_return_percent,
                2,
            ),

            buy_hold_return_percent=round(
                buy_hold_return_percent,
                2,
            ),

            excess_return_percent=round(
                excess_return_percent,
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

            total_commission_cost=round(
                total_commission_cost,
                2,
            ),

            total_slippage_cost=round(
                total_slippage_cost,
                2,
            ),

            total_execution_cost=round(
                total_execution_cost,
                2,
            ),

            execution_cost_percent_of_initial_cash=round(
                execution_cost_percent,
                2,
            ),

            return_reduction_percent=round(
                return_reduction_percent,
                2,
            ),

            average_cost_per_trade=round(
                average_cost_per_trade,
                2,
            ),

            average_slippage_cost_per_trade=round(
                average_slippage_per_trade,
                2,
            ),

            average_commission_per_trade=round(
                average_commission_per_trade,
                2,
            ),

            settings=settings,

            trades=[
                trade.to_dict()
                for trade in trades
            ],

            equity_curve=equity_curve,
        )

    except Exception as error:
        return create_failed_realistic_result(
            symbol=normalized_symbol,

            initial_cash=initial_cash,
            settings=settings,

            started_at=started_at,
            error=error,
        )


def save_realistic_execution_result(
    result: RealisticExecutionResult,
) -> tuple[Path, Path]:
    """
    현실적 체결 백테스트 결과를 JSON으로 저장합니다.
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
            f"{result.symbol}_realistic_execution_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_realistic_execution_"
            "latest.json"
        )
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
    )

    payload = result.to_dict()

    for path in (
        report_path,
        latest_path,
    ):
        with path.open(
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

    return (
        report_path,
        latest_path,
    )


def print_realistic_execution_result(
    result: RealisticExecutionResult,
) -> None:
    """
    현실적 체결 백테스트 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 118)
    print(
        f"{result.symbol} V7.8 "
        "REALISTIC EXECUTION RESULT"
    )
    print("=" * 118)

    if not result.success:
        print(
            "Status                    : FAILED"
        )

        print(
            f"Error type                : "
            f"{result.error_type}"
        )

        print(
            f"Error message             : "
            f"{result.error_message}"
        )

        print("=" * 118)
        return

    print(
        f"Period                    : "
        f"{result.data_start_date} "
        f"to {result.data_end_date}"
    )

    print(
        f"Initial cash              : "
        f"${result.initial_cash:,.2f}"
    )

    print(
        f"Final value               : "
        f"${result.final_value:,.2f}"
    )

    print()
    print("PERFORMANCE")
    print("-" * 118)

    print(
        f"Gross baseline return     : "
        f"{result.gross_baseline_return_percent:.2f}%"
    )

    print(
        f"Realistic net return      : "
        f"{result.net_return_percent:.2f}%"
    )

    print(
        f"Return reduction          : "
        f"{result.return_reduction_percent:.2f}%p"
    )

    print(
        f"Buy and hold return       : "
        f"{result.buy_hold_return_percent:.2f}%"
    )

    print(
        f"Excess return             : "
        f"{result.excess_return_percent:+.2f}%p"
    )

    print()
    print("RISK AND TRADE QUALITY")
    print("-" * 118)

    print(
        f"Total trades              : "
        f"{result.total_trades}"
    )

    print(
        f"Winning trades            : "
        f"{result.winning_trades}"
    )

    print(
        f"Losing trades             : "
        f"{result.losing_trades}"
    )

    print(
        f"Win rate                  : "
        f"{result.win_rate_percent:.2f}%"
    )

    print(
        f"Average trade return      : "
        f"{result.average_trade_return_percent:.2f}%"
    )

    print(
        f"Average win               : "
        f"{result.average_win_percent:.2f}%"
    )

    print(
        f"Average loss              : "
        f"{result.average_loss_percent:.2f}%"
    )

    print(
        f"Best trade                : "
        f"{result.best_trade_percent:.2f}%"
    )

    print(
        f"Worst trade               : "
        f"{result.worst_trade_percent:.2f}%"
    )

    print(
        f"Maximum drawdown          : "
        f"{result.maximum_drawdown_percent:.2f}%"
    )

    print(
        f"Sharpe ratio              : "
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
        f"Profit factor             : "
        f"{profit_factor_text}"
    )

    print(
        f"Average holding days      : "
        f"{result.average_holding_days:.2f}"
    )

    print()
    print("REAL EXECUTION COSTS")
    print("-" * 118)

    print(
        f"Commission per order      : "
        f"${result.settings['commission_per_order']:.2f}"
    )

    print(
        f"Slippage per order        : "
        f"{result.settings['slippage_percent']:.3f}%"
    )

    print(
        f"Total commissions         : "
        f"${result.total_commission_cost:,.2f}"
    )

    print(
        f"Total slippage cost       : "
        f"${result.total_slippage_cost:,.2f}"
    )

    print(
        f"Total execution cost      : "
        f"${result.total_execution_cost:,.2f}"
    )

    print(
        f"Cost / initial cash       : "
        f"{result.execution_cost_percent_of_initial_cash:.2f}%"
    )

    print(
        f"Average cost per trade    : "
        f"${result.average_cost_per_trade:,.2f}"
    )

    print(
        f"Average commission/trade  : "
        f"${result.average_commission_per_trade:,.2f}"
    )

    print(
        f"Average slippage/trade    : "
        f"${result.average_slippage_cost_per_trade:,.2f}"
    )

    print()
    print("LATEST COMPLETED TRADES")
    print("-" * 118)

    recent_trades = result.trades[
        -5:
    ]

    if not recent_trades:
        print(
            "완료된 거래가 없습니다."
        )

    else:
        print(
            f"{'Entry':<12}"
            f"{'Exit':<12}"
            f"{'Shares':>8}"
            f"{'Buy Fill':>12}"
            f"{'Sell Fill':>12}"
            f"{'Net P/L':>12}"
            f"{'Return':>10}"
            f"{'Reason':>16}"
        )

        print("-" * 118)

        for trade in recent_trades:
            print(
                f"{trade['entry_date']:<12}"
                f"{trade['exit_date']:<12}"
                f"{trade['shares']:>8}"
                f"${trade['entry_fill_price']:>11.2f}"
                f"${trade['exit_fill_price']:>11.2f}"
                f"${trade['net_profit_loss']:>11.2f}"
                f"{trade['net_return_percent']:>9.2f}%"
                f"{trade['exit_reason']:>16}"
            )

    print("=" * 118)

    print(
        "주의: 이 결과는 과거 데이터를 이용한 체결 시뮬레이션이며 "
        "실제 브로커 주문 체결이나 미래 수익을 보장하지 않습니다."
    )