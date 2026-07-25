import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ai.schemas import StockScanResult
from config import (
    OUTPUT_DIR,
    SAVE_JSON_REPORT,
    TOP_RESULT_COUNT,
)
from portfolio.allocator import PortfolioAllocation


def format_signal(signal: str) -> str:
    """
    BUY, HOLD, SELL 신호를 정리합니다.
    """

    normalized = (
        str(signal)
        .upper()
        .strip()
    )

    if normalized not in {
        "BUY",
        "HOLD",
        "SELL",
    }:
        return "HOLD"

    return normalized


def format_risk_level(
    risk_level: str,
) -> str:
    """
    위험도 표시를 짧게 정리합니다.
    """

    normalized = (
        str(risk_level)
        .upper()
        .strip()
    )

    mapping = {
        "LOW": "LOW",
        "MEDIUM": "MED",
        "HIGH": "HIGH",
    }

    return mapping.get(
        normalized,
        "HIGH",
    )


def print_scanner_header(
    result_count: int,
) -> None:
    """
    종목 순위표 제목을 출력합니다.
    """

    print()
    print("=" * 116)
    print("AI STOCK BOT V3.4 - STOCK RANKING")
    print("=" * 116)

    print(
        f"Successfully analyzed symbols: "
        f"{result_count}"
    )

    print()


def print_ranking_table(
    results: list[StockScanResult],
) -> None:
    """
    종목 결과를 최종점수 순서로 출력합니다.
    """

    print_scanner_header(
        result_count=len(results)
    )

    if not results:
        print(
            "No stock analysis results were generated."
        )
        return

    header = (
        f"{'Rank':<6}"
        f"{'Symbol':<9}"
        f"{'Close':>12}"
        f"{'Final':>9}"
        f"{'Tech':>8}"
        f"{'Tech Sig':>11}"
        f"{'AI Sig':>9}"
        f"{'AI Conf':>10}"
        f"{'Risk':>8}"
        f"{'Return':>11}"
        f"{'Drawdown':>11}"
        f"{'Plan':>12}"
    )

    print(header)
    print("-" * 116)

    for rank, result in enumerate(
        results,
        start=1,
    ):
        technical_signal = format_signal(
            result.technical_signal
        )

        ai_signal = format_signal(
            result.ai_signal
        )

        risk_level = format_risk_level(
            result.risk_level
        )

        print(
            f"{rank:<6}"
            f"{result.symbol:<9}"
            f"${result.close:>11.2f}"
            f"{result.final_score:>9.2f}"
            f"{result.technical_score:>8}"
            f"{technical_signal:>11}"
            f"{ai_signal:>9}"
            f"{result.ai_confidence:>9}%"
            f"{risk_level:>8}"
            f"{result.backtest_return:>10.2f}%"
            f"{result.max_drawdown:>10.2f}%"
            f"{result.plan_status:>12}"
        )

    print("=" * 116)


def print_top_opportunities(
    results: list[StockScanResult],
    top_count: int = TOP_RESULT_COUNT,
) -> None:
    """
    상위 종목의 분석과 매매계획을 출력합니다.
    """

    if not results:
        return

    selected_results = results[
        :max(1, top_count)
    ]

    print()
    print("=" * 72)
    print("TOP STOCK OPPORTUNITIES")
    print("=" * 72)

    for rank, result in enumerate(
        selected_results,
        start=1,
    ):
        print()
        print("-" * 72)
        print(
            f"#{rank} {result.symbol}"
        )
        print("-" * 72)

        print(
            f"Current price      : "
            f"${result.close:,.2f}"
        )

        print(
            f"Final score        : "
            f"{result.final_score:.2f}/100"
        )

        print(
            f"Technical score    : "
            f"{result.technical_score}/100"
        )

        print(
            f"Technical signal   : "
            f"{result.technical_signal}"
        )

        print(
            f"AI signal          : "
            f"{result.ai_signal}"
        )

        print(
            f"AI confidence      : "
            f"{result.ai_confidence}%"
        )

        print(
            f"Risk level         : "
            f"{result.risk_level}"
        )

        print(
            f"Plan status        : "
            f"{result.plan_status}"
        )

        print(
            f"Entry zone         : "
            f"${result.entry_low:,.2f}"
            f" - "
            f"${result.entry_high:,.2f}"
        )

        print(
            f"Stop loss          : "
            f"${result.stop_loss:,.2f}"
        )

        print(
            f"Target 1           : "
            f"${result.target_1:,.2f}"
        )

        print(
            f"Target 2           : "
            f"${result.target_2:,.2f}"
        )

        print(
            f"Risk/Reward 2      : "
            f"{result.risk_reward_2:.2f}"
        )

        print(
            f"Holding period     : "
            f"{result.holding_period}"
        )

        print(
            f"Backtest return    : "
            f"{result.backtest_return:.2f}%"
        )

        print(
            f"Maximum drawdown   : "
            f"{result.max_drawdown:.2f}%"
        )

        print(
            f"Backtest win rate  : "
            f"{result.win_rate:.2f}%"
        )

        print()
        print("AI summary:")
        print(result.summary)

    print()
    print("=" * 72)


def convert_to_json_safe(
    value: Any,
) -> Any:
    """
    다양한 Python 객체를 JSON 저장이 가능한 값으로 바꿉니다.
    """

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            str(key): convert_to_json_safe(
                item
            )
            for key, item in value.items()
        }

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        return [
            convert_to_json_safe(item)
            for item in value
        ]

    if hasattr(value, "model_dump"):
        return convert_to_json_safe(
            value.model_dump()
        )

    if hasattr(value, "to_dict"):
        return convert_to_json_safe(
            value.to_dict()
        )

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return str(value)


def build_stock_result_record(
    rank: int,
    result: StockScanResult,
    symbol_details: dict[str, Any],
) -> dict[str, Any]:
    """
    한 종목의 JSON 기록을 만듭니다.
    """

    result_record = result.model_dump()

    result_record["rank"] = rank

    result_record[
        "technical_reasons"
    ] = convert_to_json_safe(
        symbol_details.get(
            "technical_reasons",
            [],
        )
    )

    ai_analysis = symbol_details.get(
        "ai_analysis"
    )

    if ai_analysis is not None:
        result_record[
            "ai_analysis"
        ] = convert_to_json_safe(
            ai_analysis
        )

    trade_plan = symbol_details.get(
        "trade_plan"
    )

    if trade_plan is not None:
        result_record[
            "trade_plan"
        ] = convert_to_json_safe(
            trade_plan
        )

    position_plan = symbol_details.get(
        "position_plan"
    )

    if position_plan is not None:
        result_record[
            "position_plan"
        ] = convert_to_json_safe(
            position_plan
        )

    backtest = symbol_details.get(
        "backtest",
        {},
    )

    result_record[
        "backtest_statistics"
    ] = {
        "starting_cash": backtest.get(
            "starting_cash"
        ),
        "final_cash": backtest.get(
            "final_cash"
        ),
        "final_value": backtest.get(
            "final_value"
        ),
        "total_return": backtest.get(
            "total_return"
        ),
        "trade_count": backtest.get(
            "trade_count"
        ),
        "completed_trades": backtest.get(
            "completed_trades"
        ),
        "winning_trades": backtest.get(
            "winning_trades"
        ),
        "losing_trades": backtest.get(
            "losing_trades"
        ),
        "win_rate": backtest.get(
            "win_rate"
        ),
        "average_profit": backtest.get(
            "average_profit"
        ),
        "average_loss": backtest.get(
            "average_loss"
        ),
        "profit_factor": backtest.get(
            "profit_factor"
        ),
        "max_drawdown": backtest.get(
            "max_drawdown"
        ),
        "open_position": backtest.get(
            "open_position"
        ),
        "open_shares": backtest.get(
            "open_shares"
        ),
    }

    result_record[
        "chart_path"
    ] = convert_to_json_safe(
        symbol_details.get(
            "chart_path"
        )
    )

    return convert_to_json_safe(
        result_record
    )


def build_portfolio_record(
    portfolio: PortfolioAllocation | None,
) -> dict[str, Any] | None:
    """
    포트폴리오 배분 결과를 JSON 구조로 변환합니다.
    """

    if portfolio is None:
        return None

    return {
        "account_size": (
            portfolio.account_size
        ),
        "maximum_investable_amount": (
            portfolio.maximum_investable_amount
        ),
        "total_allocated_amount": (
            portfolio.total_allocated_amount
        ),
        "cash_reserve_amount": (
            portfolio.cash_reserve_amount
        ),
        "cash_reserve_percent": (
            portfolio.cash_reserve_percent
        ),
        "total_expected_loss": (
            portfolio.total_expected_loss
        ),
        "total_expected_profit_1": (
            portfolio.total_expected_profit_1
        ),
        "total_expected_profit_2": (
            portfolio.total_expected_profit_2
        ),
        "total_account_risk_percent": (
            portfolio.total_account_risk_percent
        ),
        "selected_count": (
            portfolio.selected_count
        ),
        "rejected_count": (
            portfolio.rejected_count
        ),
        "allocations": [
            convert_to_json_safe(
                allocation
            )
            for allocation
            in portfolio.allocations
        ],
        "rejected_symbols": (
            convert_to_json_safe(
                portfolio.rejected_symbols
            )
        ),
    }


def build_json_report(
    results: list[StockScanResult],
    details: dict[str, dict[str, Any]],
    portfolio: PortfolioAllocation | None = None,
) -> dict[str, Any]:
    """
    종목 분석과 포트폴리오 배분을 포함한
    전체 JSON 리포트를 만듭니다.
    """

    generated_at = datetime.now()

    result_records = []

    for rank, result in enumerate(
        results,
        start=1,
    ):
        symbol_details = details.get(
            result.symbol,
            {},
        )

        result_record = build_stock_result_record(
            rank=rank,
            result=result,
            symbol_details=symbol_details,
        )

        result_records.append(
            result_record
        )

    report = {
        "report_name": (
            "AI Stock Bot V3.4 Report"
        ),
        "report_version": "3.4",
        "generated_at": (
            generated_at.isoformat()
        ),
        "analyzed_count": len(results),
        "top_ranked_symbol": (
            results[0].symbol
            if results
            else None
        ),
        "top_final_score": (
            results[0].final_score
            if results
            else None
        ),
        "portfolio": build_portfolio_record(
            portfolio
        ),
        "results": result_records,
    }

    return report


def save_json_report(
    results: list[StockScanResult],
    details: dict[str, dict[str, Any]],
    portfolio: PortfolioAllocation | None = None,
    filename: str = "stock_scan_report.json",
) -> str | None:
    """
    전체 분석과 포트폴리오 결과를 JSON으로 저장합니다.
    """

    if not SAVE_JSON_REPORT:
        return None

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = build_json_report(
        results=results,
        details=details,
        portfolio=portfolio,
    )

    output_path = (
        OUTPUT_DIR / filename
    )

    with output_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(
        f"JSON report saved: "
        f"{output_path}"
    )

    return str(output_path)


def print_report_summary(
    results: list[StockScanResult],
    report_path: str | None,
) -> None:
    """
    프로그램 종료 전 핵심 결과를 출력합니다.
    """

    print()
    print("=" * 72)
    print("SCAN COMPLETED")
    print("=" * 72)

    print(
        f"Successful results : "
        f"{len(results)}"
    )

    if results:
        best_result = results[0]

        print(
            f"Top ranked stock   : "
            f"{best_result.symbol}"
        )

        print(
            f"Top final score    : "
            f"{best_result.final_score:.2f}/100"
        )

        print(
            f"Top AI signal      : "
            f"{best_result.ai_signal}"
        )

    if report_path:
        print(
            f"JSON report        : "
            f"{report_path}"
        )

    print("=" * 72)