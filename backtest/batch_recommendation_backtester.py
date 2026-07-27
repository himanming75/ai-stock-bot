import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from backtest.recommendation_backtester import (
    StrategyBacktestResult,
    run_recommendation_backtest,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "output"
    / "strategy_backtests"
    / "batch"
)


@dataclass
class BatchBacktestResult:
    """
    여러 종목 백테스트 결과를 하나로 묶습니다.
    """

    version: str

    started_at: str
    finished_at: str
    elapsed_seconds: float

    total_symbols: int
    successful_count: int
    failed_count: int

    top_symbol: str | None
    top_score: float | None

    settings: dict[str, Any]

    rankings: list[dict[str, Any]]
    results: list[dict[str, Any]]
    failures: list[dict[str, Any]]

    report_path: str | None = None
    latest_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_symbols(
    symbols: list[str],
) -> list[str]:
    """
    종목 코드를 대문자로 정리하고
    빈 값과 중복 값을 제거합니다.
    """

    cleaned_symbols: list[str] = []

    for symbol in symbols:
        normalized_symbol = (
            str(symbol)
            .upper()
            .strip()
        )

        if not normalized_symbol:
            continue

        if normalized_symbol not in cleaned_symbols:
            cleaned_symbols.append(
                normalized_symbol
            )

    return cleaned_symbols


def calculate_batch_score(
    result: StrategyBacktestResult,
) -> float:
    """
    여러 백테스트 결과를 비교하기 위한 점수입니다.

    높은 수익률, 높은 Sharpe Ratio,
    낮은 최대 낙폭, 충분한 거래 횟수를 반영합니다.
    """

    if not result.success:
        return 0.0

    score = 50.0

    strategy_return = (
        result.total_return_percent
    )

    sharpe_ratio = (
        result.sharpe_ratio
    )

    maximum_drawdown = abs(
        result.maximum_drawdown_percent
    )

    win_rate = (
        result.win_rate_percent
    )

    total_trades = (
        result.total_trades
    )

    profit_factor = (
        result.profit_factor
    )

    # 전략 수익률
    if strategy_return >= 200:
        score += 20.0

    elif strategy_return >= 100:
        score += 16.0

    elif strategy_return >= 50:
        score += 12.0

    elif strategy_return >= 20:
        score += 8.0

    elif strategy_return > 0:
        score += 4.0

    else:
        score -= 15.0

    # Sharpe Ratio
    if sharpe_ratio >= 2.0:
        score += 18.0

    elif sharpe_ratio >= 1.5:
        score += 14.0

    elif sharpe_ratio >= 1.0:
        score += 10.0

    elif sharpe_ratio >= 0.5:
        score += 5.0

    else:
        score -= 8.0

    # 최대 낙폭
    if maximum_drawdown <= 5:
        score += 12.0

    elif maximum_drawdown <= 10:
        score += 9.0

    elif maximum_drawdown <= 20:
        score += 4.0

    elif maximum_drawdown <= 30:
        score -= 3.0

    else:
        score -= 12.0

    # 승률
    if win_rate >= 60:
        score += 8.0

    elif win_rate >= 50:
        score += 5.0

    elif win_rate >= 40:
        score += 1.0

    else:
        score -= 5.0

    # Profit Factor
    if profit_factor >= 2.0:
        score += 10.0

    elif profit_factor >= 1.5:
        score += 7.0

    elif profit_factor >= 1.2:
        score += 4.0

    elif profit_factor < 1.0:
        score -= 8.0

    # 거래 횟수
    if total_trades >= 100:
        score += 5.0

    elif total_trades >= 30:
        score += 3.0

    elif total_trades < 10:
        score -= 5.0

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


def build_ranking_row(
    rank: int,
    result: StrategyBacktestResult,
) -> dict[str, Any]:
    """
    순위표 한 줄을 생성합니다.
    """

    batch_score = calculate_batch_score(
        result
    )

    return {
        "rank": rank,

        "symbol": result.symbol,

        "batch_score": batch_score,

        "strategy_return_percent": (
            result.total_return_percent
        ),

        "buy_hold_return_percent": (
            result.buy_hold_return_percent
        ),

        "excess_return_percent": round(
            result.total_return_percent
            - result.buy_hold_return_percent,
            2,
        ),

        "total_trades": (
            result.total_trades
        ),

        "win_rate_percent": (
            result.win_rate_percent
        ),

        "maximum_drawdown_percent": (
            result.maximum_drawdown_percent
        ),

        "sharpe_ratio": (
            result.sharpe_ratio
        ),

        "profit_factor": (
            result.profit_factor
        ),

        "average_trade_return_percent": (
            result.average_trade_return_percent
        ),

        "average_holding_days": (
            result.average_holding_days
        ),
    }


def run_batch_recommendation_backtest(
    symbols: list[str],
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
) -> BatchBacktestResult:
    """
    여러 종목의 추천 전략 백테스트를 일괄 실행합니다.
    """

    cleaned_symbols = normalize_symbols(
        symbols
    )

    if not cleaned_symbols:
        raise ValueError(
            "백테스트할 종목이 없습니다."
        )

    started_at = datetime.now()

    settings = {
        "symbols": cleaned_symbols,
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

    successful_results: list[
        StrategyBacktestResult
    ] = []

    failed_results: list[
        StrategyBacktestResult
    ] = []

    print()
    print("=" * 88)
    print(
        "AI STOCK BOT V7.1 "
        "MULTI-SYMBOL STRATEGY BACKTEST"
    )
    print("=" * 88)

    print(
        f"Symbols              : "
        f"{', '.join(cleaned_symbols)}"
    )

    print(
        f"Total symbols        : "
        f"{len(cleaned_symbols)}"
    )

    print(
        f"Period               : "
        f"{period}"
    )

    print("=" * 88)

    for index, symbol in enumerate(
        cleaned_symbols,
        start=1,
    ):
        print()
        print("#" * 88)
        print(
            f"[{index}/{len(cleaned_symbols)}] "
            f"{symbol}"
        )
        print("#" * 88)

        result = run_recommendation_backtest(
            symbol=symbol,

            period=period,
            interval=interval,

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

            commission_per_trade=(
                commission_per_trade
            ),
        )

        if result.success:
            successful_results.append(
                result
            )

            print(
                f"{symbol} completed: "
                f"Return "
                f"{result.total_return_percent:.2f}% | "
                f"Sharpe {result.sharpe_ratio:.2f} | "
                f"Drawdown "
                f"{result.maximum_drawdown_percent:.2f}%"
            )

        else:
            failed_results.append(
                result
            )

            print(
                f"{symbol} failed: "
                f"{result.error_type} - "
                f"{result.error_message}"
            )

    successful_results.sort(
        key=lambda item: (
            calculate_batch_score(
                item
            ),
            item.sharpe_ratio,
            item.total_return_percent,
        ),
        reverse=True,
    )

    rankings = [
        build_ranking_row(
            rank=index,
            result=result,
        )
        for index, result in enumerate(
            successful_results,
            start=1,
        )
    ]

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    top_symbol = None
    top_score = None

    if rankings:
        top_symbol = rankings[0][
            "symbol"
        ]

        top_score = rankings[0][
            "batch_score"
        ]

    return BatchBacktestResult(
        version="V7.1",

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

        total_symbols=len(
            cleaned_symbols
        ),

        successful_count=len(
            successful_results
        ),

        failed_count=len(
            failed_results
        ),

        top_symbol=top_symbol,
        top_score=top_score,

        settings=settings,

        rankings=rankings,

        results=[
            result.to_dict()
            for result in successful_results
        ],

        failures=[
            {
                "symbol": result.symbol,
                "error_type": result.error_type,
                "error_message": (
                    result.error_message
                ),
            }
            for result in failed_results
        ],
    )


def save_batch_backtest_result(
    result: BatchBacktestResult,
) -> tuple[Path, Path]:
    """
    멀티 종목 백테스트 결과를 JSON으로 저장합니다.
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
            "batch_strategy_backtest_"
            f"{timestamp}.json"
        )
    )

    latest_path = (
        OUTPUT_DIRECTORY
        / "batch_strategy_backtest_latest.json"
    )

    result.report_path = str(
        report_path
    )

    result.latest_path = str(
        latest_path
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


def print_batch_backtest_result(
    result: BatchBacktestResult,
) -> None:
    """
    멀티 종목 백테스트 순위표를 출력합니다.
    """

    print()
    print("=" * 114)
    print(
        "AI STOCK BOT V7.1 "
        "STRATEGY BACKTEST RANKING"
    )
    print("=" * 114)

    print(
        f"Total symbols        : "
        f"{result.total_symbols}"
    )

    print(
        f"Successful           : "
        f"{result.successful_count}"
    )

    print(
        f"Failed               : "
        f"{result.failed_count}"
    )

    print(
        f"Elapsed time         : "
        f"{result.elapsed_seconds:.2f} seconds"
    )

    print(
        f"Top symbol           : "
        f"{result.top_symbol or 'N/A'}"
    )

    if result.top_score is not None:
        print(
            f"Top score            : "
            f"{result.top_score:.2f}/100"
        )

    else:
        print(
            "Top score            : N/A"
        )

    print()
    print(
        f"{'Rank':<6}"
        f"{'Symbol':<9}"
        f"{'Score':>8}"
        f"{'Return':>11}"
        f"{'BuyHold':>11}"
        f"{'Excess':>11}"
        f"{'Trades':>9}"
        f"{'WinRate':>10}"
        f"{'Drawdown':>11}"
        f"{'Sharpe':>9}"
        f"{'PF':>8}"
    )

    print("-" * 114)

    for row in result.rankings:
        print(
            f"{row['rank']:<6}"
            f"{row['symbol']:<9}"
            f"{row['batch_score']:>8.2f}"
            f"{row['strategy_return_percent']:>10.2f}%"
            f"{row['buy_hold_return_percent']:>10.2f}%"
            f"{row['excess_return_percent']:>10.2f}%"
            f"{row['total_trades']:>9}"
            f"{row['win_rate_percent']:>9.2f}%"
            f"{row['maximum_drawdown_percent']:>10.2f}%"
            f"{row['sharpe_ratio']:>9.2f}"
            f"{row['profit_factor']:>8.2f}"
        )

    print("=" * 114)

    if result.failures:
        print()
        print("FAILED SYMBOLS")
        print("-" * 114)

        for failure in result.failures:
            print(
                f"{failure['symbol']}: "
                f"{failure['error_type']} - "
                f"{failure['error_message']}"
            )

    print()
    print(
        "주의: 이 결과는 과거 데이터 기반 "
        "기술적 전략 테스트이며 미래 수익을 보장하지 않습니다."
    )