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
from forecast.predictor import TradePlan, create_trade_plan
from portfolio.manager import PositionPlan, create_position_plan
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

        score = int(
            score_result["score"]
        )

        signal = determine_signal(
            row,
            score,
        )

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
    AI 의견과 신뢰도를 0~100점으로 변환합니다.
    """

    confidence = int(
        ai_analysis.confidence
    )

    if confidence <= 0:
        return float(
            technical_score
        )

    if ai_analysis.signal == "BUY":
        return float(
            confidence
        )

    if ai_analysis.signal == "HOLD":
        return 50.0

    if ai_analysis.signal == "SELL":
        return float(
            100 - confidence
        )

    return 50.0


def calculate_trade_plan_score(
    trade_plan: TradePlan,
) -> float:
    """
    매매계획의 Risk/Reward와 상태를
    종목 순위에 사용할 점수로 변환합니다.
    """

    status_scores = {
        "ATTRACTIVE": 100.0,
        "WATCH": 70.0,
        "WEAK": 40.0,
        "AVOID": 10.0,
    }

    status_score = status_scores.get(
        trade_plan.plan_status,
        40.0,
    )

    # Risk/Reward 2가 3 이상이면 100점
    risk_reward_score = min(
        100.0,
        max(
            0.0,
            trade_plan.risk_reward_2
            / 3.0
            * 100.0,
        ),
    )

    plan_score = (
        status_score * 0.60
        + risk_reward_score * 0.40
    )

    return round(
        plan_score,
        2,
    )


def calculate_final_score(
    technical_score: int,
    ai_analysis: AIStockAnalysis,
    trade_plan: TradePlan,
) -> float:
    """
    기술점수, AI 평가, 매매계획을 합쳐
    최종 종목점수를 계산합니다.

    기술점수: 50%
    AI 점수:  30%
    계획점수: 20%
    """

    ai_score = calculate_ai_opportunity_score(
        ai_analysis=ai_analysis,
        technical_score=technical_score,
    )

    plan_score = calculate_trade_plan_score(
        trade_plan=trade_plan,
    )

    final_score = (
        technical_score * 0.50
        + ai_score * 0.30
        + plan_score * 0.20
    )

    return round(
        max(
            0.0,
            min(
                100.0,
                final_score,
            ),
        ),
        2,
    )


def get_latest_analysis(
    data: pd.DataFrame,
) -> tuple[
    pd.Series,
    int,
    str,
    list[str],
]:
    """
    최근 데이터의 점수, 신호, 이유를 반환합니다.
    """

    if data.empty:
        raise ValueError(
            "분석할 시장 데이터가 없습니다."
        )

    latest = data.iloc[-1]

    score_result = calculate_score(
        latest
    )

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
        close=float(
            latest["Close"]
        ),
        ma5=float(
            latest["MA5"]
        ),
        ma20=float(
            latest["MA20"]
        ),
        rsi=float(
            latest["RSI"]
        ),
        macd=float(
            latest["MACD"]
        ),
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


def print_trade_plan_summary(
    trade_plan: TradePlan,
) -> None:
    """
    종목 스캔 중 매매계획 핵심값을 출력합니다.
    """

    print(
        f"Plan status      : "
        f"{trade_plan.plan_status}"
    )

    print(
        f"Entry zone       : "
        f"${trade_plan.entry_low:,.2f}"
        f" - "
        f"${trade_plan.entry_high:,.2f}"
    )

    print(
        f"Stop loss        : "
        f"${trade_plan.stop_loss:,.2f}"
    )

    print(
        f"Target 1         : "
        f"${trade_plan.target_1:,.2f}"
    )

    print(
        f"Target 2         : "
        f"${trade_plan.target_2:,.2f}"
    )

    print(
        f"Risk/Reward 2    : "
        f"{trade_plan.risk_reward_2:.2f}"
    )

    print(
        f"Holding period   : "
        f"{trade_plan.holding_period}"
    )


def print_position_plan_summary(
    position_plan: PositionPlan,
) -> None:
    """
    종목 스캔 중 포지션 크기와 예상 손익을 출력합니다.
    """

    print(
        f"Position status  : "
        f"{position_plan.position_status}"
    )

    print(
        f"Recommended shares: "
        f"{position_plan.recommended_shares}"
    )

    print(
        f"Investment amount : "
        f"${position_plan.investment_amount:,.2f}"
    )

    print(
        f"Position percent  : "
        f"{position_plan.position_percent:.2f}%"
    )

    print(
        f"Expected loss     : "
        f"${position_plan.expected_loss_amount:,.2f}"
    )

    print(
        f"Expected profit 1 : "
        f"${position_plan.expected_profit_1:,.2f}"
    )

    print(
        f"Expected profit 2 : "
        f"${position_plan.expected_profit_2:,.2f}"
    )

    print(
        f"Account risk      : "
        f"{position_plan.actual_account_risk_percent:.2f}%"
    )


def scan_stock(
    symbol: str,
) -> tuple[
    StockScanResult,
    dict[str, Any],
]:
    """
    한 종목의 전체 분석을 실행합니다.

    순서:
    1. 데이터 다운로드
    2. 기술점수와 신호
    3. AI 분석
    4. 백테스트
    5. 기술적 매매계획
    6. 포지션 크기 계산
    7. 최종점수
    8. 차트 저장
    """

    symbol = (
        str(symbol)
        .upper()
        .strip()
    )

    if not symbol:
        raise ValueError(
            "종목 코드가 비어 있습니다."
        )

    print()
    print("=" * 60)
    print(f"SCANNING {symbol}")
    print("=" * 60)

    # 1. 시장 데이터 다운로드
    data = get_history(
        symbol=symbol,
        period=MARKET_PERIOD,
        interval=MARKET_INTERVAL,
    )

    # 2. 전체 날짜에 점수와 신호 추가
    data = add_scores_and_signals(
        data
    )

    (
        latest,
        technical_score,
        technical_signal,
        reasons,
    ) = get_latest_analysis(
        data
    )

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

    # 3. AI 분석
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

    # 4. 백테스트
    print("Running backtest...")

    backtest_result = run_backtest(
        data=data,
        starting_cash=STARTING_CASH,
    )

    # 5. 기술적 매매계획
    print("Creating trade plan...")

    trade_plan = create_trade_plan(
        symbol=symbol,
        data=data,
        technical_signal=technical_signal,
    )

    print_trade_plan_summary(
        trade_plan
    )

    # 6. 포지션 크기 계산
    print("Creating position plan...")

    position_plan = create_position_plan(
        trade_plan=trade_plan,
    )

    print_position_plan_summary(
        position_plan
    )

    # 7. 최종점수
    final_score = calculate_final_score(
        technical_score=technical_score,
        ai_analysis=ai_analysis,
        trade_plan=trade_plan,
    )

    print(
        f"Final score      : "
        f"{final_score:.2f}/100"
    )

    print(
        f"Backtest return  : "
        f"{backtest_result['total_return']:.2f}%"
    )

    # 8. 차트 저장
    chart_path = None

    if SAVE_CHARTS:
        chart_path = plot_backtest(
            data=data,
            trades=backtest_result["trades"],
            symbol=symbol,
            show_chart=SHOW_CHARTS,
        )

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

        plan_status=trade_plan.plan_status,

        entry_low=trade_plan.entry_low,
        entry_high=trade_plan.entry_high,

        stop_loss=trade_plan.stop_loss,
        target_1=trade_plan.target_1,
        target_2=trade_plan.target_2,

        expected_gain_1=trade_plan.expected_gain_1,
        expected_gain_2=trade_plan.expected_gain_2,
        expected_loss=trade_plan.expected_loss,

        risk_reward_1=trade_plan.risk_reward_1,
        risk_reward_2=trade_plan.risk_reward_2,

        atr=trade_plan.atr,
        volatility_percent=(
            trade_plan.volatility_percent
        ),

        holding_period=trade_plan.holding_period,

        summary=ai_analysis.summary,
    )

    details = {
        "data": data,
        "latest": latest,
        "technical_reasons": reasons,
        "ai_analysis": ai_analysis,
        "backtest": backtest_result,
        "trade_plan": trade_plan,
        "position_plan": position_plan,
        "chart_path": chart_path,
    }

    return (
        scan_result,
        details,
    )


def scan_stocks(
    symbols: list[str],
) -> tuple[
    list[StockScanResult],
    dict[str, dict[str, Any]],
]:
    """
    여러 종목을 순서대로 분석합니다.

    한 종목에서 오류가 발생해도
    나머지 종목 분석을 계속합니다.
    """

    results: list[
        StockScanResult
    ] = []

    all_details: dict[
        str,
        dict[str, Any],
    ] = {}

    total_symbols = len(
        symbols
    )

    print()
    print("=" * 60)
    print("AI STOCK BOT V3 SCANNER")
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

            results.append(
                result
            )

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

    results.sort(
        key=lambda item: item.final_score,
        reverse=True,
    )

    return (
        results,
        all_details,
    )