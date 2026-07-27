import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtest.realistic_execution import (
    RealisticExecutionResult,
    calculate_buy_fill_price,
    calculate_sell_fill_price,
    run_realistic_execution_backtest,
)
from backtest.recommendation_backtester import (
    calculate_maximum_drawdown,
    calculate_sharpe_ratio,
    normalize_symbol,
    prepare_backtest_data,
    safe_float,
)
from data.market import get_history


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "execution_consistency"
)


@dataclass
class LockedExecutionTrade:
    """
    기준 거래 경로를 고정하고 비용만 다르게 적용한 거래입니다.
    """

    trade_number: int
    symbol: str

    entry_date: str
    exit_date: str

    market_entry_price: float
    entry_fill_price: float

    market_exit_price: float
    exit_fill_price: float

    shares: int
    exit_reason: str
    holding_days: int

    entry_market_value: float
    exit_market_value: float

    entry_fill_value: float
    exit_fill_value: float

    entry_commission: float
    exit_commission: float
    total_commission: float

    entry_slippage_cost: float
    exit_slippage_cost: float
    total_slippage_cost: float

    total_execution_cost: float

    net_entry_cost: float
    net_exit_proceeds: float

    net_profit_loss: float
    net_return_percent: float

    cash_before_entry: float
    cash_after_entry: float
    cash_after_exit: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConsistencyScenarioResult:
    """
    한 가지 비용 조건의 실행 결과입니다.
    """

    scenario_number: int
    scenario_name: str

    commission_per_order: float
    slippage_percent: float

    success: bool

    initial_cash: float
    final_value: float

    net_return_percent: float
    return_reduction_percent: float

    total_trades: int
    expected_trades: int

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

    total_commission_cost: float
    total_slippage_cost: float
    total_execution_cost: float

    cost_percent_of_initial_cash: float
    average_cost_per_trade: float

    trade_path_match: bool
    trade_count_difference: int

    date_path_match: bool
    price_path_match: bool
    exit_reason_path_match: bool

    status: str

    trades: list[dict[str, Any]]
    equity_curve: list[dict[str, Any]]

    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionConsistencyResult:
    """
    전체 V7.9 Execution Consistency 테스트 결과입니다.
    """

    version: str
    symbol: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    data_start_date: str
    data_end_date: str
    total_rows: int

    initial_cash: float

    baseline_trade_count: int
    baseline_final_value: float
    baseline_return_percent: float
    baseline_sharpe_ratio: float
    baseline_drawdown_percent: float
    baseline_profit_factor: float

    total_scenarios: int
    successful_scenarios: int
    failed_scenarios: int

    matching_trade_paths: int
    mismatched_trade_paths: int
    path_consistency_percent: float

    profitable_scenarios: int
    acceptable_scenarios: int

    profitable_percent: float
    acceptable_percent: float

    average_net_return_percent: float
    worst_net_return_percent: float

    average_sharpe_ratio: float
    worst_sharpe_ratio: float

    average_drawdown_percent: float
    worst_drawdown_percent: float

    average_execution_cost: float
    maximum_execution_cost: float

    average_return_reduction_percent: float
    maximum_return_reduction_percent: float

    consistency_score: float
    validation_status: str
    overfitting_warning: bool

    reasons: list[str]
    warnings: list[str]

    scenarios: list[dict[str, Any]]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def safe_average(
    values: list[float],
) -> float:
    """
    숫자 목록의 평균을 안전하게 계산합니다.
    """

    if not values:
        return 0.0

    return round(
        float(np.mean(values)),
        2,
    )


def validate_scenario_settings(
    commission_per_order: float,
    slippage_percent: float,
) -> None:
    """
    비용 시나리오 설정값을 검사합니다.
    """

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


def determine_scenario_status(
    net_return_percent: float,
    sharpe_ratio: float,
    maximum_drawdown_percent: float,
    profit_factor: float,
) -> str:
    """
    한 가지 비용 시나리오의 상태를 판정합니다.
    """

    if (
        net_return_percent > 0
        and sharpe_ratio >= 1.0
        and profit_factor >= 1.40
        and abs(maximum_drawdown_percent) <= 10.0
    ):
        return "ROBUST"

    if (
        net_return_percent > 0
        and sharpe_ratio >= 0.60
        and profit_factor >= 1.15
        and abs(maximum_drawdown_percent) <= 15.0
    ):
        return "ACCEPTABLE"

    if net_return_percent > 0:
        return "WEAK"

    return "UNPROFITABLE"


def build_locked_schedule(
    baseline: RealisticExecutionResult,
) -> list[dict[str, Any]]:
    """
    비용 없는 기준 백테스트의 거래를 순서대로 고정합니다.
    """

    if not baseline.success:
        raise RuntimeError(
            baseline.error_message
            or "비용 없는 기준 백테스트가 실패했습니다."
        )

    if not baseline.trades:
        raise RuntimeError(
            "기준 백테스트에 완료된 거래가 없습니다."
        )

    schedule: list[dict[str, Any]] = []

    for trade_number, trade in enumerate(
        baseline.trades,
        start=1,
    ):
        entry_date = str(
            trade["entry_date"]
        )

        exit_date = str(
            trade["exit_date"]
        )

        schedule.append(
            {
                "trade_number": trade_number,

                "entry_date": entry_date,
                "exit_date": exit_date,

                "market_entry_price": safe_float(
                    trade["market_entry_price"]
                ),

                "market_exit_price": safe_float(
                    trade["market_exit_price"]
                ),

                "exit_reason": str(
                    trade["exit_reason"]
                ),

                "holding_days": int(
                    trade["holding_days"]
                ),
            }
        )

    return schedule


def calculate_replay_profit_factor(
    trades: list[LockedExecutionTrade],
) -> float:
    """
    순손익을 이용해 Profit Factor를 계산합니다.
    """

    total_profit = sum(
        max(
            trade.net_profit_loss,
            0.0,
        )
        for trade in trades
    )

    total_loss = abs(
        sum(
            min(
                trade.net_profit_loss,
                0.0,
            )
            for trade in trades
        )
    )

    if total_loss > 0:
        return round(
            total_profit / total_loss,
            2,
        )

    if total_profit > 0:
        return float("inf")

    return 0.0


def build_date_close_map(
    data: pd.DataFrame,
) -> dict[str, float]:
    """
    날짜별 종가를 빠르게 조회하기 위한 사전을 생성합니다.
    """

    date_close_map: dict[str, float] = {}

    for timestamp, row in data.iterrows():
        date_text = pd.Timestamp(
            timestamp
        ).strftime(
            "%Y-%m-%d"
        )

        date_close_map[
            date_text
        ] = safe_float(
            row["Close"]
        )

    return date_close_map


def verify_locked_path(
    locked_schedule: list[dict[str, Any]],
    completed_trades: list[LockedExecutionTrade],
) -> tuple[
    bool,
    bool,
    bool,
    bool,
]:
    """
    거래 횟수, 날짜, 시장가격, 청산 사유를 검사합니다.
    """

    count_match = (
        len(locked_schedule)
        == len(completed_trades)
    )

    if not count_match:
        return (
            False,
            False,
            False,
            False,
        )

    date_path_match = True
    price_path_match = True
    exit_reason_path_match = True

    for expected, actual in zip(
        locked_schedule,
        completed_trades,
        strict=True,
    ):
        if (
            str(expected["entry_date"])
            != actual.entry_date
            or str(expected["exit_date"])
            != actual.exit_date
        ):
            date_path_match = False

        expected_entry_price = safe_float(
            expected[
                "market_entry_price"
            ]
        )

        expected_exit_price = safe_float(
            expected[
                "market_exit_price"
            ]
        )

        if (
            abs(
                expected_entry_price
                - actual.market_entry_price
            )
            > 0.0001
            or abs(
                expected_exit_price
                - actual.market_exit_price
            )
            > 0.0001
        ):
            price_path_match = False

        if (
            str(expected["exit_reason"])
            != actual.exit_reason
        ):
            exit_reason_path_match = False

    overall_match = (
        count_match
        and date_path_match
        and price_path_match
        and exit_reason_path_match
    )

    return (
        overall_match,
        date_path_match,
        price_path_match,
        exit_reason_path_match,
    )


def replay_locked_trade_path(
    symbol: str,
    data: pd.DataFrame,
    locked_schedule: list[dict[str, Any]],

    initial_cash: float,
    position_percent: float,

    commission_per_order: float,
    slippage_percent: float,

    scenario_number: int,
    scenario_name: str,

    baseline_return_percent: float,
) -> ConsistencyScenarioResult:
    """
    고정된 거래를 1번부터 마지막 거래까지 순서대로 재생합니다.

    진입일, 청산일, 시장가격, 청산 사유는 절대 변경하지 않고
    수수료와 슬리피지만 변경합니다.
    """

    validate_scenario_settings(
        commission_per_order=(
            commission_per_order
        ),

        slippage_percent=(
            slippage_percent
        ),
    )

    normalized_symbol = normalize_symbol(
        symbol
    )

    if not locked_schedule:
        raise RuntimeError(
            "고정 거래 경로가 비어 있습니다."
        )

    date_close_map = build_date_close_map(
        data
    )

    data_dates = set(
        date_close_map.keys()
    )

    cash = float(
        initial_cash
    )

    total_commission_cost = 0.0
    total_slippage_cost = 0.0

    completed_trades: list[
        LockedExecutionTrade
    ] = []

    equity_events: list[
        dict[str, Any]
    ] = []

    for schedule_index, scheduled_trade in enumerate(
        locked_schedule,
        start=1,
    ):
        trade_number = int(
            scheduled_trade[
                "trade_number"
            ]
        )

        entry_date = str(
            scheduled_trade[
                "entry_date"
            ]
        )

        exit_date = str(
            scheduled_trade[
                "exit_date"
            ]
        )

        if entry_date not in data_dates:
            raise RuntimeError(
                f"Trade {trade_number}: "
                f"진입일 {entry_date}이 시장 데이터에 없습니다."
            )

        if exit_date not in data_dates:
            raise RuntimeError(
                f"Trade {trade_number}: "
                f"청산일 {exit_date}이 시장 데이터에 없습니다."
            )

        market_entry_price = safe_float(
            scheduled_trade[
                "market_entry_price"
            ]
        )

        market_exit_price = safe_float(
            scheduled_trade[
                "market_exit_price"
            ]
        )

        if market_entry_price <= 0:
            raise RuntimeError(
                f"Trade {trade_number}: "
                "진입 시장가격이 0 이하입니다."
            )

        if market_exit_price <= 0:
            raise RuntimeError(
                f"Trade {trade_number}: "
                "청산 시장가격이 0 이하입니다."
            )

        entry_fill_price = (
            calculate_buy_fill_price(
                market_price=(
                    market_entry_price
                ),

                slippage_percent=(
                    slippage_percent
                ),
            )
        )

        cash_before_entry = cash

        position_budget = (
            cash
            * position_percent
            / 100.0
        )

        available_for_shares = max(
            0.0,
            position_budget
            - commission_per_order,
        )

        shares = int(
            available_for_shares
            // entry_fill_price
        )

        if shares <= 0:
            raise RuntimeError(
                f"Trade {trade_number}: "
                f"{entry_date} 진입 수량이 0입니다."
            )

        entry_fill_value = (
            shares
            * entry_fill_price
        )

        total_entry_cash = (
            entry_fill_value
            + commission_per_order
        )

        if total_entry_cash > cash:
            raise RuntimeError(
                f"Trade {trade_number}: "
                "진입 금액이 보유 현금을 초과했습니다."
            )

        cash -= total_entry_cash

        entry_market_value = (
            shares
            * market_entry_price
        )

        entry_slippage_cost = max(
            0.0,
            entry_fill_value
            - entry_market_value,
        )

        total_commission_cost += (
            commission_per_order
        )

        total_slippage_cost += (
            entry_slippage_cost
        )

        cash_after_entry = cash

        equity_events.append(
            {
                "date": entry_date,
                "event_order": 1,
                "event": "ENTRY",

                "trade_number": trade_number,

                "cash": round(
                    cash,
                    2,
                ),

                "shares": shares,

                "market_price": round(
                    market_entry_price,
                    4,
                ),

                "fill_price": round(
                    entry_fill_price,
                    4,
                ),

                "market_value": round(
                    shares
                    * date_close_map[
                        entry_date
                    ],
                    2,
                ),

                "equity": round(
                    cash
                    + (
                        shares
                        * date_close_map[
                            entry_date
                        ]
                    ),
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

        exit_fill_price = (
            calculate_sell_fill_price(
                market_price=(
                    market_exit_price
                ),

                slippage_percent=(
                    slippage_percent
                ),
            )
        )

        exit_market_value = (
            shares
            * market_exit_price
        )

        exit_fill_value = (
            shares
            * exit_fill_price
        )

        exit_slippage_cost = max(
            0.0,
            exit_market_value
            - exit_fill_value,
        )

        net_exit_proceeds = (
            exit_fill_value
            - commission_per_order
        )

        cash += net_exit_proceeds

        total_commission_cost += (
            commission_per_order
        )

        total_slippage_cost += (
            exit_slippage_cost
        )

        net_entry_cost = (
            entry_fill_value
            + commission_per_order
        )

        net_profit_loss = (
            net_exit_proceeds
            - net_entry_cost
        )

        net_return_percent = (
            (
                net_profit_loss
                / net_entry_cost
            )
            * 100.0
            if net_entry_cost > 0
            else 0.0
        )

        total_commission = (
            commission_per_order
            * 2.0
        )

        total_slippage = (
            entry_slippage_cost
            + exit_slippage_cost
        )

        total_execution_cost = (
            total_commission
            + total_slippage
        )

        completed_trade = LockedExecutionTrade(
            trade_number=trade_number,
            symbol=normalized_symbol,

            entry_date=entry_date,
            exit_date=exit_date,

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

            exit_reason=str(
                scheduled_trade[
                    "exit_reason"
                ]
            ),

            holding_days=int(
                scheduled_trade[
                    "holding_days"
                ]
            ),

            entry_market_value=round(
                entry_market_value,
                2,
            ),

            exit_market_value=round(
                exit_market_value,
                2,
            ),

            entry_fill_value=round(
                entry_fill_value,
                2,
            ),

            exit_fill_value=round(
                exit_fill_value,
                2,
            ),

            entry_commission=round(
                commission_per_order,
                2,
            ),

            exit_commission=round(
                commission_per_order,
                2,
            ),

            total_commission=round(
                total_commission,
                2,
            ),

            entry_slippage_cost=round(
                entry_slippage_cost,
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

            net_entry_cost=round(
                net_entry_cost,
                2,
            ),

            net_exit_proceeds=round(
                net_exit_proceeds,
                2,
            ),

            net_profit_loss=round(
                net_profit_loss,
                2,
            ),

            net_return_percent=round(
                net_return_percent,
                2,
            ),

            cash_before_entry=round(
                cash_before_entry,
                2,
            ),

            cash_after_entry=round(
                cash_after_entry,
                2,
            ),

            cash_after_exit=round(
                cash,
                2,
            ),
        )

        completed_trades.append(
            completed_trade
        )

        equity_events.append(
            {
                "date": exit_date,
                "event_order": 2,
                "event": "EXIT",

                "trade_number": trade_number,

                "cash": round(
                    cash,
                    2,
                ),

                "shares": 0,

                "market_price": round(
                    market_exit_price,
                    4,
                ),

                "fill_price": round(
                    exit_fill_price,
                    4,
                ),

                "market_value": 0.0,

                "equity": round(
                    cash,
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

    equity_events.sort(
        key=lambda item: (
            item["date"],
            item["trade_number"],
            item["event_order"],
        )
    )

    final_value = float(
        cash
    )

    net_return_percent = (
        (
            final_value
            - initial_cash
        )
        / initial_cash
    ) * 100.0

    return_reduction_percent = (
        baseline_return_percent
        - net_return_percent
    )

    trade_returns = [
        trade.net_return_percent
        for trade in completed_trades
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
        completed_trades
    )

    expected_trades = len(
        locked_schedule
    )

    winning_trades = len(
        winning_returns
    )

    losing_trades = len(
        losing_returns
    )

    win_rate_percent = (
        (
            winning_trades
            / total_trades
        )
        * 100.0
        if total_trades > 0
        else 0.0
    )

    average_trade_return = safe_average(
        trade_returns
    )

    average_win = safe_average(
        winning_returns
    )

    average_loss = safe_average(
        losing_returns
    )

    best_trade = (
        max(trade_returns)
        if trade_returns
        else 0.0
    )

    worst_trade = (
        min(trade_returns)
        if trade_returns
        else 0.0
    )

    equity_values = [
        safe_float(
            item["equity"]
        )
        for item in equity_events
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
        calculate_replay_profit_factor(
            completed_trades
        )
    )

    total_execution_cost = (
        total_commission_cost
        + total_slippage_cost
    )

    cost_percent = (
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

    trade_count_difference = (
        total_trades
        - expected_trades
    )

    (
        trade_path_match,
        date_path_match,
        price_path_match,
        exit_reason_path_match,
    ) = verify_locked_path(
        locked_schedule=(
            locked_schedule
        ),

        completed_trades=(
            completed_trades
        ),
    )

    status = determine_scenario_status(
        net_return_percent=(
            net_return_percent
        ),

        sharpe_ratio=(
            sharpe_ratio
        ),

        maximum_drawdown_percent=(
            maximum_drawdown
        ),

        profit_factor=(
            profit_factor
        ),
    )

    return ConsistencyScenarioResult(
        scenario_number=scenario_number,
        scenario_name=scenario_name,

        commission_per_order=round(
            commission_per_order,
            2,
        ),

        slippage_percent=round(
            slippage_percent,
            4,
        ),

        success=True,

        initial_cash=round(
            initial_cash,
            2,
        ),

        final_value=round(
            final_value,
            2,
        ),

        net_return_percent=round(
            net_return_percent,
            2,
        ),

        return_reduction_percent=round(
            return_reduction_percent,
            2,
        ),

        total_trades=total_trades,
        expected_trades=expected_trades,

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
            average_win,
            2,
        ),

        average_loss_percent=round(
            average_loss,
            2,
        ),

        best_trade_percent=round(
            best_trade,
            2,
        ),

        worst_trade_percent=round(
            worst_trade,
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

        cost_percent_of_initial_cash=round(
            cost_percent,
            2,
        ),

        average_cost_per_trade=round(
            average_cost_per_trade,
            2,
        ),

        trade_path_match=(
            trade_path_match
        ),

        trade_count_difference=(
            trade_count_difference
        ),

        date_path_match=(
            date_path_match
        ),

        price_path_match=(
            price_path_match
        ),

        exit_reason_path_match=(
            exit_reason_path_match
        ),

        status=status,

        trades=[
            trade.to_dict()
            for trade in completed_trades
        ],

        equity_curve=equity_events,
    )


def create_failed_scenario(
    scenario_number: int,
    scenario_name: str,

    commission_per_order: float,
    slippage_percent: float,

    initial_cash: float,
    baseline_trade_count: int,

    error: Exception,
) -> ConsistencyScenarioResult:
    """
    실패한 시나리오 결과를 생성합니다.
    """

    return ConsistencyScenarioResult(
        scenario_number=(
            scenario_number
        ),

        scenario_name=(
            scenario_name
        ),

        commission_per_order=(
            commission_per_order
        ),

        slippage_percent=(
            slippage_percent
        ),

        success=False,

        initial_cash=(
            initial_cash
        ),

        final_value=(
            initial_cash
        ),

        net_return_percent=0.0,
        return_reduction_percent=0.0,

        total_trades=0,
        expected_trades=(
            baseline_trade_count
        ),

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

        total_commission_cost=0.0,
        total_slippage_cost=0.0,
        total_execution_cost=0.0,

        cost_percent_of_initial_cash=0.0,
        average_cost_per_trade=0.0,

        trade_path_match=False,

        trade_count_difference=(
            -baseline_trade_count
        ),

        date_path_match=False,
        price_path_match=False,
        exit_reason_path_match=False,

        status="FAILED",

        trades=[],
        equity_curve=[],

        error_type=(
            type(error).__name__
        ),

        error_message=str(
            error
        ),
    )


def evaluate_consistency_result(
    scenarios: list[
        ConsistencyScenarioResult
    ],

    baseline_return_percent: float,
) -> tuple[
    float,
    str,
    bool,
    list[str],
    list[str],
]:
    """
    전체 비용 일관성 결과를 평가합니다.
    """

    successful = [
        scenario
        for scenario in scenarios
        if scenario.success
    ]

    if not successful:
        return (
            0.0,
            "FAILED",
            True,
            [],
            [
                "성공한 비용 시나리오가 없습니다."
            ],
        )

    matching = [
        scenario
        for scenario in successful
        if scenario.trade_path_match
    ]

    profitable = [
        scenario
        for scenario in successful
        if scenario.net_return_percent > 0
    ]

    acceptable = [
        scenario
        for scenario in successful
        if scenario.status
        in {
            "ROBUST",
            "ACCEPTABLE",
        }
    ]

    path_percent = (
        len(matching)
        / len(successful)
        * 100.0
    )

    profitable_percent = (
        len(profitable)
        / len(successful)
        * 100.0
    )

    acceptable_percent = (
        len(acceptable)
        / len(successful)
        * 100.0
    )

    worst_return = min(
        scenario.net_return_percent
        for scenario in successful
    )

    maximum_reduction = max(
        scenario.return_reduction_percent
        for scenario in successful
    )

    score = 0.0

    reasons: list[str] = []
    warnings: list[str] = []

    if path_percent == 100.0:
        score += 30.0

        reasons.append(
            "모든 비용 시나리오에서 거래 횟수, 날짜, "
            "시장가격 및 청산 사유가 일치했습니다."
        )

    elif path_percent >= 80.0:
        score += 20.0

        warnings.append(
            "일부 비용 시나리오의 거래 경로가 "
            "기준 경로와 다릅니다."
        )

    else:
        warnings.append(
            "거래 경로 일관성이 충분하지 않습니다."
        )

    if profitable_percent == 100.0:
        score += 25.0

        reasons.append(
            "모든 비용 조건에서 플러스 수익을 유지했습니다."
        )

    elif profitable_percent >= 75.0:
        score += 18.0

    elif profitable_percent >= 50.0:
        score += 10.0

    else:
        warnings.append(
            "비용 적용 후 수익 유지 비율이 낮습니다."
        )

    if acceptable_percent >= 75.0:
        score += 20.0

        reasons.append(
            "대부분의 비용 조건에서 위험 조정 "
            "성과 기준을 통과했습니다."
        )

    elif acceptable_percent >= 50.0:
        score += 12.0

    else:
        warnings.append(
            "비용 적용 후 품질 기준을 통과한 "
            "시나리오가 부족합니다."
        )

    if worst_return > 0:
        score += 15.0

        reasons.append(
            "가장 높은 비용 조건에서도 "
            "순수익이 플러스입니다."
        )

    else:
        warnings.append(
            "일부 비용 조건에서 수익률이 "
            "0% 이하로 하락했습니다."
        )

    if maximum_reduction <= 15.0:
        score += 10.0

    elif maximum_reduction <= 30.0:
        score += 5.0

        warnings.append(
            "높은 비용 조건에서 수익 감소 폭이 큽니다."
        )

    else:
        warnings.append(
            "거래 비용에 따른 최대 수익 감소 폭이 "
            "30%p를 초과했습니다."
        )

    score = round(
        min(
            score,
            100.0,
        ),
        2,
    )

    overfitting_warning = (
        path_percent < 100.0
        or profitable_percent < 100.0
        or acceptable_percent < 50.0
        or maximum_reduction > 30.0
    )

    if (
        score >= 85.0
        and not overfitting_warning
    ):
        validation_status = "ROBUST"

    elif score >= 65.0:
        validation_status = "ACCEPTABLE"

    elif score >= 45.0:
        validation_status = "WEAK"

    else:
        validation_status = "COST_SENSITIVE"

    if baseline_return_percent <= 0:
        warnings.append(
            "기준 비용 없는 전략 수익률이 "
            "0% 이하입니다."
        )

    return (
        score,
        validation_status,
        overfitting_warning,
        reasons,
        warnings,
    )


def run_execution_consistency_validation(
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

    scenarios: list[
        dict[str, Any]
    ] | None = None,
) -> ExecutionConsistencyResult:
    """
    비용 없는 거래 경로를 만든 뒤 모든 조건에서
    거래 순서를 고정하여 비용만 변경합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    started_at = datetime.now()

    if scenarios is None:
        scenarios = [
            {
                "name": "ZERO_COST",

                "commission_per_order": 0.0,
                "slippage_percent": 0.00,
            },

            {
                "name": "LOW_SLIPPAGE",

                "commission_per_order": 0.0,
                "slippage_percent": 0.05,
            },

            {
                "name": "STANDARD_COST",

                "commission_per_order": 1.0,
                "slippage_percent": 0.05,
            },

            {
                "name": "HIGH_COST",

                "commission_per_order": 2.0,
                "slippage_percent": 0.10,
            },
        ]

    print()
    print("=" * 140)
    print(
        f"{normalized_symbol} V7.9 "
        "EXECUTION CONSISTENCY VALIDATION"
    )
    print("=" * 140)

    print(
        "Creating zero-cost baseline trade path..."
    )

    baseline = (
        run_realistic_execution_backtest(
            symbol=normalized_symbol,

            period=period,
            interval=interval,

            initial_cash=initial_cash,

            position_percent=(
                position_percent
            ),

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

            commission_per_order=0.0,
            slippage_percent=0.0,
        )
    )

    if not baseline.success:
        raise RuntimeError(
            baseline.error_message
            or "기준 거래 경로 생성에 실패했습니다."
        )

    locked_schedule = build_locked_schedule(
        baseline
    )

    print(
        f"Baseline trades           : "
        f"{len(locked_schedule)}"
    )

    print(
        f"Baseline return           : "
        f"{baseline.net_return_percent:.2f}%"
    )

    print(
        "Downloading market data for locked replay..."
    )

    raw_data = get_history(
        symbol=normalized_symbol,
        period=period,
        interval=interval,
    )

    data = prepare_backtest_data(
        raw_data
    )

    data_start_date = pd.Timestamp(
        data.index[0]
    ).strftime(
        "%Y-%m-%d"
    )

    data_end_date = pd.Timestamp(
        data.index[-1]
    ).strftime(
        "%Y-%m-%d"
    )

    print(
        f"Replay period             : "
        f"{data_start_date} to {data_end_date}"
    )

    print(
        f"Total scenarios           : "
        f"{len(scenarios)}"
    )

    print("=" * 140)

    scenario_results: list[
        ConsistencyScenarioResult
    ] = []

    for scenario_number, scenario in enumerate(
        scenarios,
        start=1,
    ):
        scenario_name = str(
            scenario.get(
                "name",
                f"SCENARIO_{scenario_number}",
            )
        )

        commission_per_order = float(
            scenario.get(
                "commission_per_order",
                0.0,
            )
        )

        slippage_percent = float(
            scenario.get(
                "slippage_percent",
                0.0,
            )
        )

        try:
            result = replay_locked_trade_path(
                symbol=normalized_symbol,
                data=data,

                locked_schedule=(
                    locked_schedule
                ),

                initial_cash=initial_cash,

                position_percent=(
                    position_percent
                ),

                commission_per_order=(
                    commission_per_order
                ),

                slippage_percent=(
                    slippage_percent
                ),

                scenario_number=(
                    scenario_number
                ),

                scenario_name=(
                    scenario_name
                ),

                baseline_return_percent=(
                    baseline.net_return_percent
                ),
            )

            scenario_results.append(
                result
            )

            profit_factor_text = (
                "INF"
                if np.isinf(
                    result.profit_factor
                )
                else f"{result.profit_factor:.2f}"
            )

            print(
                f"[{scenario_number}/{len(scenarios)}] "
                f"{scenario_name:<18} | "
                f"Trades "
                f"{result.total_trades:>3}/"
                f"{result.expected_trades:<3} | "
                f"Return "
                f"{result.net_return_percent:>7.2f}% | "
                f"Sharpe "
                f"{result.sharpe_ratio:>5.2f} | "
                f"DD "
                f"{result.maximum_drawdown_percent:>7.2f}% | "
                f"PF "
                f"{profit_factor_text:>5} | "
                f"Path "
                f"{result.trade_path_match} | "
                f"{result.status}"
            )

        except Exception as error:
            failed = create_failed_scenario(
                scenario_number=(
                    scenario_number
                ),

                scenario_name=(
                    scenario_name
                ),

                commission_per_order=(
                    commission_per_order
                ),

                slippage_percent=(
                    slippage_percent
                ),

                initial_cash=(
                    initial_cash
                ),

                baseline_trade_count=len(
                    locked_schedule
                ),

                error=error,
            )

            scenario_results.append(
                failed
            )

            print(
                f"[{scenario_number}/{len(scenarios)}] "
                f"{scenario_name} FAILED: "
                f"{type(error).__name__} - "
                f"{error}"
            )

    successful = [
        scenario
        for scenario in scenario_results
        if scenario.success
    ]

    failed = [
        scenario
        for scenario in scenario_results
        if not scenario.success
    ]

    if not successful:
        raise RuntimeError(
            "성공한 Execution Consistency "
            "시나리오가 없습니다."
        )

    matching = [
        scenario
        for scenario in successful
        if scenario.trade_path_match
    ]

    profitable = [
        scenario
        for scenario in successful
        if scenario.net_return_percent > 0
    ]

    acceptable = [
        scenario
        for scenario in successful
        if scenario.status
        in {
            "ROBUST",
            "ACCEPTABLE",
        }
    ]

    path_consistency_percent = (
        len(matching)
        / len(successful)
        * 100.0
    )

    profitable_percent = (
        len(profitable)
        / len(successful)
        * 100.0
    )

    acceptable_percent = (
        len(acceptable)
        / len(successful)
        * 100.0
    )

    (
        consistency_score,
        validation_status,
        overfitting_warning,
        reasons,
        warnings,
    ) = evaluate_consistency_result(
        scenarios=(
            scenario_results
        ),

        baseline_return_percent=(
            baseline.net_return_percent
        ),
    )

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    return ExecutionConsistencyResult(
        version="V7.9",
        symbol=normalized_symbol,

        started_at=(
            started_at.isoformat()
        ),

        finished_at=(
            finished_at.isoformat()
        ),

        elapsed_seconds=round(
            elapsed_seconds,
            2,
        ),

        data_start_date=(
            data_start_date
        ),

        data_end_date=(
            data_end_date
        ),

        total_rows=len(
            data
        ),

        initial_cash=round(
            initial_cash,
            2,
        ),

        baseline_trade_count=len(
            locked_schedule
        ),

        baseline_final_value=(
            baseline.final_value
        ),

        baseline_return_percent=(
            baseline.net_return_percent
        ),

        baseline_sharpe_ratio=(
            baseline.sharpe_ratio
        ),

        baseline_drawdown_percent=(
            baseline.maximum_drawdown_percent
        ),

        baseline_profit_factor=(
            baseline.profit_factor
        ),

        total_scenarios=len(
            scenario_results
        ),

        successful_scenarios=len(
            successful
        ),

        failed_scenarios=len(
            failed
        ),

        matching_trade_paths=len(
            matching
        ),

        mismatched_trade_paths=(
            len(successful)
            - len(matching)
        ),

        path_consistency_percent=round(
            path_consistency_percent,
            2,
        ),

        profitable_scenarios=len(
            profitable
        ),

        acceptable_scenarios=len(
            acceptable
        ),

        profitable_percent=round(
            profitable_percent,
            2,
        ),

        acceptable_percent=round(
            acceptable_percent,
            2,
        ),

        average_net_return_percent=(
            safe_average(
                [
                    scenario.net_return_percent
                    for scenario in successful
                ]
            )
        ),

        worst_net_return_percent=round(
            min(
                scenario.net_return_percent
                for scenario in successful
            ),
            2,
        ),

        average_sharpe_ratio=(
            safe_average(
                [
                    scenario.sharpe_ratio
                    for scenario in successful
                ]
            )
        ),

        worst_sharpe_ratio=round(
            min(
                scenario.sharpe_ratio
                for scenario in successful
            ),
            2,
        ),

        average_drawdown_percent=(
            safe_average(
                [
                    scenario.maximum_drawdown_percent
                    for scenario in successful
                ]
            )
        ),

        worst_drawdown_percent=round(
            min(
                scenario.maximum_drawdown_percent
                for scenario in successful
            ),
            2,
        ),

        average_execution_cost=(
            safe_average(
                [
                    scenario.total_execution_cost
                    for scenario in successful
                ]
            )
        ),

        maximum_execution_cost=round(
            max(
                scenario.total_execution_cost
                for scenario in successful
            ),
            2,
        ),

        average_return_reduction_percent=(
            safe_average(
                [
                    scenario.return_reduction_percent
                    for scenario in successful
                ]
            )
        ),

        maximum_return_reduction_percent=round(
            max(
                scenario.return_reduction_percent
                for scenario in successful
            ),
            2,
        ),

        consistency_score=(
            consistency_score
        ),

        validation_status=(
            validation_status
        ),

        overfitting_warning=(
            overfitting_warning
        ),

        reasons=reasons,
        warnings=warnings,

        scenarios=[
            scenario.to_dict()
            for scenario in scenario_results
        ],
    )


def save_execution_consistency_result(
    result: ExecutionConsistencyResult,
) -> tuple[Path, Path]:
    """
    V7.9 결과를 JSON 파일로 저장합니다.
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
            f"{result.symbol}_execution_consistency_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / (
            f"{result.symbol}_execution_consistency_"
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


def print_execution_consistency_result(
    result: ExecutionConsistencyResult,
) -> None:
    """
    V7.9 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 150)
    print(
        f"{result.symbol} V7.9 "
        "EXECUTION CONSISTENCY RESULT"
    )
    print("=" * 150)

    print(
        f"Period                       : "
        f"{result.data_start_date} "
        f"to {result.data_end_date}"
    )

    print(
        f"Validation status            : "
        f"{result.validation_status}"
    )

    print(
        f"Consistency score            : "
        f"{result.consistency_score:.2f}/100"
    )

    print(
        f"Overfitting warning          : "
        f"{result.overfitting_warning}"
    )

    print()
    print("ZERO-COST BASELINE")
    print("-" * 150)

    print(
        f"Baseline trades              : "
        f"{result.baseline_trade_count}"
    )

    print(
        f"Baseline final value         : "
        f"${result.baseline_final_value:,.2f}"
    )

    print(
        f"Baseline return              : "
        f"{result.baseline_return_percent:.2f}%"
    )

    print(
        f"Baseline Sharpe              : "
        f"{result.baseline_sharpe_ratio:.2f}"
    )

    print(
        f"Baseline drawdown            : "
        f"{result.baseline_drawdown_percent:.2f}%"
    )

    print(
        f"Baseline profit factor       : "
        f"{result.baseline_profit_factor:.2f}"
    )

    print()
    print("CONSISTENCY SUMMARY")
    print("-" * 150)

    print(
        f"Total scenarios              : "
        f"{result.total_scenarios}"
    )

    print(
        f"Successful scenarios         : "
        f"{result.successful_scenarios}"
    )

    print(
        f"Failed scenarios             : "
        f"{result.failed_scenarios}"
    )

    print(
        f"Matching trade paths         : "
        f"{result.matching_trade_paths}/"
        f"{result.successful_scenarios}"
    )

    print(
        f"Path consistency             : "
        f"{result.path_consistency_percent:.2f}%"
    )

    print(
        f"Profitable scenarios         : "
        f"{result.profitable_scenarios}/"
        f"{result.successful_scenarios} "
        f"({result.profitable_percent:.2f}%)"
    )

    print(
        f"Acceptable scenarios         : "
        f"{result.acceptable_scenarios}/"
        f"{result.successful_scenarios} "
        f"({result.acceptable_percent:.2f}%)"
    )

    print()
    print("PERFORMANCE SUMMARY")
    print("-" * 150)

    print(
        f"Average net return           : "
        f"{result.average_net_return_percent:.2f}%"
    )

    print(
        f"Worst net return             : "
        f"{result.worst_net_return_percent:.2f}%"
    )

    print(
        f"Average Sharpe               : "
        f"{result.average_sharpe_ratio:.2f}"
    )

    print(
        f"Worst Sharpe                 : "
        f"{result.worst_sharpe_ratio:.2f}"
    )

    print(
        f"Average drawdown             : "
        f"{result.average_drawdown_percent:.2f}%"
    )

    print(
        f"Worst drawdown               : "
        f"{result.worst_drawdown_percent:.2f}%"
    )

    print(
        f"Average execution cost       : "
        f"${result.average_execution_cost:,.2f}"
    )

    print(
        f"Maximum execution cost       : "
        f"${result.maximum_execution_cost:,.2f}"
    )

    print(
        f"Average return reduction     : "
        f"{result.average_return_reduction_percent:.2f}%p"
    )

    print(
        f"Maximum return reduction     : "
        f"{result.maximum_return_reduction_percent:.2f}%p"
    )

    print()
    print("LOCKED-PATH SCENARIO RESULTS")
    print("-" * 150)

    print(
        f"{'No.':<5}"
        f"{'Scenario':<20}"
        f"{'Comm.':>9}"
        f"{'Slip.':>9}"
        f"{'Trades':>11}"
        f"{'Path':>8}"
        f"{'Return':>11}"
        f"{'Reduction':>12}"
        f"{'Sharpe':>9}"
        f"{'DD':>10}"
        f"{'PF':>8}"
        f"{'Costs':>13}"
        f"{'Status':>14}"
    )

    print("-" * 150)

    successful = [
        scenario
        for scenario in result.scenarios
        if scenario["success"]
    ]

    successful.sort(
        key=lambda scenario: (
            scenario[
                "scenario_number"
            ]
        )
    )

    for scenario in successful:
        profit_factor = float(
            scenario[
                "profit_factor"
            ]
        )

        profit_factor_text = (
            "INF"
            if np.isinf(
                profit_factor
            )
            else f"{profit_factor:.2f}"
        )

        trade_text = (
            f"{scenario['total_trades']}/"
            f"{scenario['expected_trades']}"
        )

        print(
            f"{scenario['scenario_number']:<5}"
            f"{scenario['scenario_name']:<20}"
            f"${scenario['commission_per_order']:>7.2f}"
            f"{scenario['slippage_percent']:>8.3f}%"
            f"{trade_text:>11}"
            f"{str(scenario['trade_path_match']):>8}"
            f"{scenario['net_return_percent']:>10.2f}%"
            f"{scenario['return_reduction_percent']:>11.2f}%p"
            f"{scenario['sharpe_ratio']:>9.2f}"
            f"{scenario['maximum_drawdown_percent']:>9.2f}%"
            f"{profit_factor_text:>8}"
            f"${scenario['total_execution_cost']:>11,.2f}"
            f"{scenario['status']:>14}"
        )

    if result.reasons:
        print()
        print("REASONS")

        for reason in result.reasons:
            print(
                f"- {reason}"
            )

    if result.warnings:
        print()
        print("WARNINGS")

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    print("=" * 150)

    print(
        "주의: 모든 비용 시나리오는 기준 거래 순서, "
        "진입일, 청산일, 시장가격 및 청산 사유를 고정했습니다."
    )

    print(
        "이 결과는 과거 데이터 기반 시뮬레이션이며 "
        "실제 주문 체결이나 미래 수익을 보장하지 않습니다."
    )