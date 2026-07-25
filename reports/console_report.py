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


def format_signal(signal: str) -> str:
    """
    BUY, HOLD, SELL 신호를 일정한 길이로 반환합니다.
    """

    normalized = str(signal).upper().strip()

    if normalized not in {
        "BUY",
        "HOLD",
        "SELL",
    }:
        return "HOLD"

    return normalized


def format_risk_level(risk_level: str) -> str:
    """
    위험도 표시를 일정하게 정리합니다.
    """

    normalized = str(risk_level).upper().strip()

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
    전체 종목 스캐너 결과 제목을 출력합니다.
    """

    print()
    print("=" * 110)
    print("AI STOCK BOT V2 - STOCK RANKING")
    print("=" * 110)
    print(
        f"Successfully analyzed symbols: "
        f"{result_count}"
    )
    print()


def print_ranking_table(
    results: list[StockScanResult],
) -> None:
    """
    종목 결과를 최종점수 순으로 표 형태로 출력합니다.
    """

    print_scanner_header(
        result_count=len(results)
    )

    if not results:
        print("No stock analysis results were generated.")
        return

    header = (
        f"{'Rank':<6}"
        f"{'Symbol':<9}"
        f"{'Close':>11}"
        f"{'Final':>9}"
        f"{'Tech':>8}"
        f"{'Tech Sig':>11}"
        f"{'AI Sig':>9}"
        f"{'AI Conf':>10}"
        f"{'Risk':>8}"
        f"{'Return':>11}"
        f"{'Drawdown':>11}"
    )

    print(header)
    print("-" * 110)

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
            f"${result.close:>10.2f}"
            f"{result.final_score:>9.2f}"
            f"{result.technical_score:>8}"
            f"{technical_signal:>11}"
            f"{ai_signal:>9}"
            f"{result.ai_confidence:>9}%"
            f"{risk_level:>8}"
            f"{result.backtest_return:>10.2f}%"
            f"{result.max_drawdown:>10.2f}%"
        )

    print("=" * 110)


def print_top_opportunities(
    results: list[StockScanResult],
    top_count: int = TOP_RESULT_COUNT,
) -> None:
    """
    상위 종목의 핵심 설명을 자세히 출력합니다.
    """

    if not results:
        return

    selected_results = results[
        :max(1, top_count)
    ]

    print()
    print("=" * 70)
    print("TOP STOCK OPPORTUNITIES")
    print("=" * 70)

    for rank, result in enumerate(
        selected_results,
        start=1,
    ):
        print()
        print("-" * 70)
        print(
            f"#{rank} {result.symbol}"
        )
        print("-" * 70)

        print(
            f"Current price     : "
            f"${result.close:,.2f}"
        )

        print(
            f"Final score       : "
            f"{result.final_score:.2f}/100"
        )

        print(
            f"Technical score   : "
            f"{result.technical_score}/100"
        )

        print(
            f"Technical signal  : "
            f"{result.technical_signal}"
        )

        print(
            f"AI signal         : "
            f"{result.ai_signal}"
        )

        print(
            f"AI confidence     : "
            f"{result.ai_confidence}%"
        )

        print(
            f"Risk level        : "
            f"{result.risk_level}"
        )

        print(
            f"Backtest return   : "
            f"{result.backtest_return:.2f}%"
        )

        print(
            f"Maximum drawdown  : "
            f"{result.max_drawdown:.2f}%"
        )

        print(
            f"Backtest win rate : "
            f"{result.win_rate:.2f}%"
        )

        print()
        print("AI summary:")
        print(result.summary)

    print()
    print("=" * 70)


def convert_to_json_safe(
    value: Any,
) -> Any:
    """
    JSON 저장이 어려운 객체를 안전한 형태로 변환합니다.
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

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return str(value)


def build_json_report(
    results: list[StockScanResult],
    details: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    JSON 파일로 저장할 전체 리포트 구조를 만듭니다.
    """

    generated_at = datetime.now()

    result_records = []

    for rank, result in enumerate(
        results,
        start=1,
    ):
        result_record = result.model_dump()

        result_record["rank"] = rank

        symbol_details = details.get(
            result.symbol,
            {},
        )

        technical_reasons = (
            symbol_details.get(
                "technical_reasons",
                [],
            )
        )

        ai_analysis = symbol_details.get(
            "ai_analysis"
        )

        backtest = symbol_details.get(
            "backtest",
            {},
        )

        result_record[
            "technical_reasons"
        ] = convert_to_json_safe(
            technical_reasons
        )

        if ai_analysis is not None:
            result_record[
                "ai_analysis"
            ] = convert_to_json_safe(
                ai_analysis
            )

        result_record[
            "backtest_statistics"
        ] = {
            "starting_cash": backtest.get(
                "starting_cash"
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
            "profit_factor": backtest.get(
                "profit_factor"
            ),
            "max_drawdown": backtest.get(
                "max_drawdown"
            ),
        }

        result_record[
            "chart_path"
        ] = convert_to_json_safe(
            symbol_details.get(
                "chart_path"
            )
        )

        result_records.append(
            convert_to_json_safe(
                result_record
            )
        )

    report = {
        "report_name": (
            "AI Stock Bot V2 Scan Report"
        ),
        "generated_at": (
            generated_at.isoformat()
        ),
        "analyzed_count": len(results),
        "results": result_records,
    }

    return report


def save_json_report(
    results: list[StockScanResult],
    details: dict[str, dict[str, Any]],
    filename: str = "stock_scan_report.json",
) -> str | None:
    """
    전체 스캔 결과를 JSON 파일로 저장합니다.
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
    프로그램 종료 전 간단한 결과를 출력합니다.
    """

    print()
    print("=" * 70)
    print("SCAN COMPLETED")
    print("=" * 70)

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

    print("=" * 70)