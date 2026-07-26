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


def normalize_text(value: Any) -> str:
    """
    문자열 값을 대문자로 정리합니다.
    """

    return str(value).upper().strip()


def format_signal(signal: str) -> str:
    """
    BUY, HOLD, SELL 값을 정리합니다.
    """

    normalized = normalize_text(signal)

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
    위험도 값을 짧게 표시합니다.
    """

    mapping = {
        "LOW": "LOW",
        "MEDIUM": "MED",
        "HIGH": "HIGH",
    }

    return mapping.get(
        normalize_text(risk_level),
        "HIGH",
    )


def format_ml_prediction(
    prediction: str,
) -> str:
    """
    머신러닝 예측값을 짧게 표시합니다.
    """

    mapping = {
        "BULLISH": "BULL",
        "NEUTRAL": "NEUTRAL",
        "BEARISH": "BEAR",
        "UNAVAILABLE": "N/A",
    }

    return mapping.get(
        normalize_text(prediction),
        "N/A",
    )


def format_ml_status(
    model_status: str,
) -> str:
    """
    머신러닝 모델 상태를 짧게 표시합니다.
    """

    mapping = {
        "USABLE": "USABLE",
        "PROMISING": "PROMISING",
        "EXPERIMENTAL": "EXPERIMENT",
        "WEAK": "WEAK",
        "LOW_DATA": "LOW_DATA",
        "UNAVAILABLE": "N/A",
    }

    return mapping.get(
        normalize_text(model_status),
        "N/A",
    )


def print_scanner_header(
    result_count: int,
) -> None:
    """
    종목 순위표 제목을 출력합니다.
    """

    print()
    print("=" * 158)
    print("AI STOCK BOT V4.3 - STOCK RANKING WITH MACHINE LEARNING")
    print("=" * 158)

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
        f"{'Rank':<5}"
        f"{'Symbol':<8}"
        f"{'Close':>11}"
        f"{'Final':>8}"
        f"{'Tech':>7}"
        f"{'Tech Sig':>10}"
        f"{'AI Sig':>8}"
        f"{'AI Conf':>9}"
        f"{'ML':>10}"
        f"{'ML Up':>9}"
        f"{'ML Bal':>9}"
        f"{'ML Status':>12}"
        f"{'Risk':>7}"
        f"{'Return':>10}"
        f"{'Drawdown':>11}"
        f"{'Plan':>12}"
    )

    print(header)
    print("-" * 158)

    for rank, result in enumerate(
        results,
        start=1,
    ):
        print(
            f"{rank:<5}"
            f"{result.symbol:<8}"
            f"${result.close:>10.2f}"
            f"{result.final_score:>8.2f}"
            f"{result.technical_score:>7}"
            f"{format_signal(result.technical_signal):>10}"
            f"{format_signal(result.ai_signal):>8}"
            f"{result.ai_confidence:>8}%"
            f"{format_ml_prediction(result.ml_prediction):>10}"
            f"{result.ml_up_probability:>8.2f}%"
            f"{result.ml_balanced_accuracy:>8.2f}%"
            f"{format_ml_status(result.ml_model_status):>12}"
            f"{format_risk_level(result.risk_level):>7}"
            f"{result.backtest_return:>9.2f}%"
            f"{result.max_drawdown:>10.2f}%"
            f"{result.plan_status:>12}"
        )

    print("=" * 158)


def print_ml_details(
    result: StockScanResult,
) -> None:
    """
    한 종목의 머신러닝 핵심 결과를 출력합니다.
    """

    print()
    print("Machine learning:")

    print(
        f"ML prediction       : "
        f"{result.ml_prediction}"
    )

    print(
        f"ML up probability   : "
        f"{result.ml_up_probability:.2f}%"
    )

    print(
        f"ML down probability : "
        f"{result.ml_down_probability:.2f}%"
    )

    print(
        f"ML validation acc.  : "
        f"{result.ml_validation_accuracy:.2f}%"
    )

    print(
        f"ML balanced acc.    : "
        f"{result.ml_balanced_accuracy:.2f}%"
    )

    print(
        f"ML model status     : "
        f"{result.ml_model_status}"
    )

    print(
        f"ML prediction date  : "
        f"{result.ml_prediction_date or 'N/A'}"
    )

    print(
        f"ML horizon          : "
        f"{result.ml_horizon_days} trading days"
    )

    print(
        f"ML feature count    : "
        f"{result.ml_feature_count}"
    )


def print_top_opportunities(
    results: list[StockScanResult],
    top_count: int = TOP_RESULT_COUNT,
) -> None:
    """
    상위 종목의 분석, 머신러닝 결과와
    매매계획을 출력합니다.
    """

    if not results:
        return

    selected_results = results[
        :max(1, top_count)
    ]

    print()
    print("=" * 80)
    print("TOP STOCK OPPORTUNITIES")
    print("=" * 80)

    for rank, result in enumerate(
        selected_results,
        start=1,
    ):
        print()
        print("-" * 80)
        print(
            f"#{rank} {result.symbol}"
        )
        print("-" * 80)

        print(
            f"Current price       : "
            f"${result.close:,.2f}"
        )

        print(
            f"Final score         : "
            f"{result.final_score:.2f}/100"
        )

        print(
            f"Technical score     : "
            f"{result.technical_score}/100"
        )

        print(
            f"Technical signal    : "
            f"{result.technical_signal}"
        )

        print(
            f"AI signal           : "
            f"{result.ai_signal}"
        )

        print(
            f"AI confidence       : "
            f"{result.ai_confidence}%"
        )

        print(
            f"Risk level          : "
            f"{result.risk_level}"
        )

        print_ml_details(
            result
        )

        print()
        print("Trade plan:")

        print(
            f"Plan status         : "
            f"{result.plan_status}"
        )

        print(
            f"Entry zone          : "
            f"${result.entry_low:,.2f}"
            f" - "
            f"${result.entry_high:,.2f}"
        )

        print(
            f"Stop loss           : "
            f"${result.stop_loss:,.2f}"
        )

        print(
            f"Target 1            : "
            f"${result.target_1:,.2f}"
        )

        print(
            f"Target 2            : "
            f"${result.target_2:,.2f}"
        )

        print(
            f"Risk/Reward 2       : "
            f"{result.risk_reward_2:.2f}"
        )

        print(
            f"Holding period      : "
            f"{result.holding_period}"
        )

        print()
        print("Backtest:")

        print(
            f"Backtest return     : "
            f"{result.backtest_return:.2f}%"
        )

        print(
            f"Maximum drawdown    : "
            f"{result.max_drawdown:.2f}%"
        )

        print(
            f"Backtest win rate   : "
            f"{result.win_rate:.2f}%"
        )

        print()
        print("AI summary:")
        print(result.summary)

    print()
    print("=" * 80)


def convert_to_json_safe(
    value: Any,
) -> Any:
    """
    Python 객체를 JSON으로 저장할 수 있는
    기본 자료형으로 변환합니다.
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
            str(key): convert_to_json_safe(item)
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


def build_backtest_record(
    backtest: dict[str, Any],
) -> dict[str, Any]:
    """
    백테스트 핵심 통계를 JSON 구조로 정리합니다.
    """

    fields = [
        "starting_cash",
        "final_cash",
        "final_value",
        "total_return",
        "trade_count",
        "completed_trades",
        "winning_trades",
        "losing_trades",
        "break_even_trades",
        "win_rate",
        "average_profit",
        "average_loss",
        "gross_profit",
        "gross_loss",
        "profit_factor",
        "max_drawdown",
        "open_position",
        "open_shares",
        "open_buy_price",
    ]

    return {
        field: convert_to_json_safe(
            backtest.get(field)
        )
        for field in fields
    }


def build_stock_result_record(
    rank: int,
    result: StockScanResult,
    symbol_details: dict[str, Any],
) -> dict[str, Any]:
    """
    한 종목의 모든 분석 결과를
    JSON 기록으로 만듭니다.
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

    ml_prediction = symbol_details.get(
        "ml_prediction"
    )

    if ml_prediction is not None:
        result_record[
            "machine_learning"
        ] = convert_to_json_safe(
            ml_prediction
        )
    else:
        result_record[
            "machine_learning"
        ] = {
            "prediction": "UNAVAILABLE",
            "model_status": "UNAVAILABLE",
        }

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
    ] = build_backtest_record(
        backtest
    )

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
    포트폴리오 배분 결과를 JSON으로 변환합니다.
    """

    if portfolio is None:
        return None

    return convert_to_json_safe(
        portfolio.to_dict()
    )


def build_ml_report_summary(
    results: list[StockScanResult],
) -> dict[str, Any]:
    """
    모든 종목의 머신러닝 결과를 요약합니다.
    """

    if not results:
        return {
            "available_count": 0,
            "average_up_probability": 0.0,
            "average_balanced_accuracy": 0.0,
            "bullish_count": 0,
            "neutral_count": 0,
            "bearish_count": 0,
        }

    available_results = [
        result
        for result in results
        if result.ml_model_status
        != "UNAVAILABLE"
    ]

    if not available_results:
        return {
            "available_count": 0,
            "average_up_probability": 0.0,
            "average_balanced_accuracy": 0.0,
            "bullish_count": 0,
            "neutral_count": 0,
            "bearish_count": 0,
        }

    average_up_probability = sum(
        result.ml_up_probability
        for result in available_results
    ) / len(available_results)

    average_balanced_accuracy = sum(
        result.ml_balanced_accuracy
        for result in available_results
    ) / len(available_results)

    return {
        "available_count": len(
            available_results
        ),
        "average_up_probability": round(
            average_up_probability,
            2,
        ),
        "average_balanced_accuracy": round(
            average_balanced_accuracy,
            2,
        ),
        "bullish_count": sum(
            result.ml_prediction == "BULLISH"
            for result in available_results
        ),
        "neutral_count": sum(
            result.ml_prediction == "NEUTRAL"
            for result in available_results
        ),
        "bearish_count": sum(
            result.ml_prediction == "BEARISH"
            for result in available_results
        ),
    }


def build_json_report(
    results: list[StockScanResult],
    details: dict[str, dict[str, Any]],
    portfolio: PortfolioAllocation | None = None,
) -> dict[str, Any]:
    """
    전체 V4.3 JSON 리포트를 만듭니다.
    """

    result_records = []

    for rank, result in enumerate(
        results,
        start=1,
    ):
        symbol_details = details.get(
            result.symbol,
            {},
        )

        result_records.append(
            build_stock_result_record(
                rank=rank,
                result=result,
                symbol_details=symbol_details,
            )
        )

    return {
        "report_name": (
            "AI Stock Bot V4.3 Report"
        ),
        "report_version": "4.3",
        "generated_at": (
            datetime.now().isoformat()
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
        "machine_learning_summary": (
            build_ml_report_summary(
                results
            )
        ),
        "portfolio": build_portfolio_record(
            portfolio
        ),
        "results": result_records,
    }


def save_json_report(
    results: list[StockScanResult],
    details: dict[str, dict[str, Any]],
    portfolio: PortfolioAllocation | None = None,
    filename: str = "stock_scan_report.json",
) -> str | None:
    """
    종목 분석, 머신러닝 및 포트폴리오 결과를
    JSON 파일로 저장합니다.
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
    print("=" * 80)
    print("SCAN COMPLETED")
    print("=" * 80)

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

        print(
            f"Top ML prediction  : "
            f"{best_result.ml_prediction}"
        )

        print(
            f"Top ML up prob.    : "
            f"{best_result.ml_up_probability:.2f}%"
        )

        print(
            f"Top ML status      : "
            f"{best_result.ml_model_status}"
        )

    if report_path:
        print(
            f"JSON report        : "
            f"{report_path}"
        )

    print("=" * 80)