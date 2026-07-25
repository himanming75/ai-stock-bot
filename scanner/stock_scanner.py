from typing import Any

import pandas as pd

from ai.analyst import analyze_technical_data
from ai.schemas import AIStockAnalysis, StockScanResult
from backtest.engine import run_backtest
from charts.backtest_chart import plot_backtest
from config import (
    MARKET_INTERVAL,
    MARKET_PERIOD,
    SAVE_CHARTS,
    SHOW_CHARTS,
    STARTING_CASH,
)
from data.market import get_history
from strategy.score import calculate_score, determine_signal


def add_scores_and_signals(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    모든 날짜에 기술점수와 매매신호를 추가합니다.
    """

    analyzed_data = data.copy()

    scores: list[int] = []
    signals: list[str] = []

    for _, row in analyzed_data.iterrows():
        score_result = calculate_score(row)

        score = int(score_result["score"])
        signal = determine_signal(row, score)

        scores.append(score)
        signals.append(signal)

    analyzed_data["Score"] = scores
    analyzed_data["Signal"] = signals

    return analyzed_data


def calculate_ai_opportunity_score(
    ai_analysis: AIStockAnalysis,
    technical_score: int,
) -> float:
    """
    AI 의견을 종목 선별용 0~100점으로 변환합니다.

    BUY:
        AI 신뢰도를 그대로 사용

    HOLD:
        중립점수 50을 중심으로 계산

    SELL:
        신뢰도가 높을수록 종목 선별점수가 낮아짐

    AI 호출 실패:
        confidence가 0이면 기술점수를 대신 사용
    """

    confidence = int(ai_analysis.confidence)

    if confidence <= 0:
        return float(technical_score)

    if ai_analysis.signal == "BUY":
        return float(confidence)

    if ai_analysis.signal == "HOLD":
        return 50.0

    if ai_analysis.signal == "SELL":
        return float(100 - confidence)

    return 50.0


def calculate_final_score(
    technical_score: int,
    ai_analysis: AIStockAnalysis,
) -> float:
    """
    기술점수와 AI 점수를 합쳐 최종점수를 계산합니다.

    기술 분석: 60%
    AI 분석:   40%
    """

    ai_score = calculate_ai_opportunity_score(
        ai_analysis=ai_analysis,
        technical_score=technical_score,
    )

    final_score = (
        technical_score * 0.60
        + ai_score * 0.40
    )

    return round(
        max(0.0, min(100.0, final_score)),
        2,
    )


def get_latest_analysis(
    data: pd.DataFrame,
) -> tuple[pd.Series, int, str, list[str]]:
    """
    가장 최근 데이터의 점수, 신호, 이유를 반환합니다.
    """

    if data.empty:
        raise ValueError(
            "분석할 시장 데이터가 없습니다."
        )

    latest = data.iloc[-1]

    score_result = calculate_score(latest)

    technical_score = int(
        score_result["score"]
    )

    technical_signal = determine_signal(
        latest,
        technical_score,
    )

    reasons = list(
        score_result["reasons"]
    )

    return (
        latest,
        technical_score,
        technical_signal,
        reasons,
    )


def run_ai_analysis(
    symbol: str,
    latest: pd.Series,
    technical_score: int,
    technical_signal: str,
) -> AIStockAnalysis:
    """
    최근 기술지표를 OpenAI에 전달합니다.
    """

    return analyze_technical_data(
        symbol=symbol,
        close=float(latest["Close"]),
        ma5=float(latest["MA5"]),
        ma20=float(latest["MA20"]),
        rsi=float(latest["RSI"]),
        macd=float(latest["MACD"]),
        macd_signal=float(
            latest["MACD_SIGNAL"]
        ),
        macd_hist=float(
            latest["MACD_HIST"]
        ),
        bb_upper=float(
            latest["BB_UPPER"]
        ),
        bb_middle=float(
            latest["BB_MIDDLE"]
        ),
        bb_lower=float(
            latest["BB_LOWER"]
        ),
        technical_score=technical_score,
        technical_signal=technical_signal,
    )


def scan_stock(
    symbol: str,
) -> tuple[StockScanResult, dict[str, Any]]:
    """
    한 종목의 전체 분석을 실행합니다.

    반환값:
    1. 종목 스캔 요약 결과
    2. 세부 데이터
    """

    symbol = str(symbol).upper().strip()

    if not symbol:
        raise ValueError(
            "종목 코드가 비어 있습니다."
        )

    print()
    print("=" * 60)
    print(f"SCANNING {symbol}")
    print("=" * 60)

    # 1. 시장 데이터 다운로드 및 기술지표 계산
    data = get_history(
        symbol=symbol,
        period=MARKET_PERIOD,
        interval=MARKET_INTERVAL,
    )

    # 2. 전체 날짜에 점수와 신호 추가
    data = add_scores_and_signals(data)

    # 3. 최신 기술분석
    (
        latest,
        technical_score,
        technical_signal,
        reasons,
    ) = get_latest_analysis(data)

    # 가장 최근 신호를 확실히 일치시킴
    data.loc[
        data.index[-1],
        "Signal",
    ] = technical_signal

    print(
        f"Technical score : "
        f"{technical_score}/100"
    )
    print(
        f"Technical signal: "
        f"{technical_signal}"
    )

    # 4. 구조화된 AI 분석
    print("Running AI analysis...")

    ai_analysis = run_ai_analysis(
        symbol=symbol,
        latest=latest,
        technical_score=technical_score,
        technical_signal=technical_signal,
    )

    print(
        f"AI signal       : "
        f"{ai_analysis.signal}"
    )
    print(
        f"AI confidence   : "
        f"{ai_analysis.confidence}%"
    )
    print(
        f"Risk level      : "
        f"{ai_analysis.risk_level}"
    )

    # 5. 백테스트
    print("Running backtest...")

    backtest_result = run_backtest(
        data=data,
        starting_cash=STARTING_CASH,
    )

    # 6. 최종 종합점수
    final_score = calculate_final_score(
        technical_score=technical_score,
        ai_analysis=ai_analysis,
    )

    print(
        f"Final score     : "
        f"{final_score:.2f}/100"
    )
    print(
        f"Backtest return : "
        f"{backtest_result['total_return']:.2f}%"
    )

    # 7. 차트 저장
    chart_path = None

    if SAVE_CHARTS:
        chart_path = plot_backtest(
            data=data,
            trades=backtest_result["trades"],
            symbol=symbol,
            show_chart=SHOW_CHARTS,
        )

    # 8. 스캔 요약 결과 객체
    scan_result = StockScanResult(
        symbol=symbol,
        close=round(
            float(latest["Close"]),
            2,
        ),
        technical_score=technical_score,
        technical_signal=technical_signal,
        ai_signal=ai_analysis.signal,
        ai_confidence=ai_analysis.confidence,
        risk_level=ai_analysis.risk_level,
        final_score=final_score,
        backtest_return=round(
            float(
                backtest_result[
                    "total_return"
                ]
            ),
            2,
        ),
        max_drawdown=round(
            float(
                backtest_result[
                    "max_drawdown"
                ]
            ),
            2,
        ),
        win_rate=round(
            float(
                backtest_result[
                    "win_rate"
                ]
            ),
            2,
        ),
        summary=ai_analysis.summary,
    )

    # 9. 나중에 상세 보고서에서 사용할 데이터
    details = {
        "data": data,
        "latest": latest,
        "technical_reasons": reasons,
        "ai_analysis": ai_analysis,
        "backtest": backtest_result,
        "chart_path": chart_path,
    }

    return scan_result, details


def scan_stocks(
    symbols: list[str],
) -> tuple[
    list[StockScanResult],
    dict[str, dict[str, Any]],
]:
    """
    여러 종목을 순서대로 분석합니다.

    한 종목에서 오류가 발생해도
    나머지 종목 분석은 계속 진행합니다.
    """

    results: list[StockScanResult] = []
    all_details: dict[
        str,
        dict[str, Any],
    ] = {}

    total_symbols = len(symbols)

    print()
    print("=" * 60)
    print("AI STOCK BOT V2 SCANNER")
    print("=" * 60)
    print(
        f"Symbols to scan: "
        f"{total_symbols}"
    )

    for index, symbol in enumerate(
        symbols,
        start=1,
    ):
        normalized_symbol = (
            str(symbol)
            .upper()
            .strip()
        )

        print()
        print(
            f"[{index}/{total_symbols}] "
            f"{normalized_symbol}"
        )

        try:
            result, details = scan_stock(
                normalized_symbol
            )

            results.append(result)

            all_details[
                normalized_symbol
            ] = details

        except Exception as error:
            print(
                f"{normalized_symbol} scan failed."
            )
            print(
                f"Error type   : "
                f"{type(error).__name__}"
            )
            print(
                f"Error message: "
                f"{error}"
            )

    # 최종점수가 높은 순서로 정렬
    results.sort(
        key=lambda item: item.final_score,
        reverse=True,
    )

    return results, all_details