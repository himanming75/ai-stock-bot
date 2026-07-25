from typing import Literal

from pydantic import BaseModel, Field


class AIStockAnalysis(BaseModel):
    """
    OpenAI가 반환해야 하는 주식 기술분석 결과 구조입니다.
    """

    trend: Literal[
        "STRONG_BULLISH",
        "BULLISH",
        "NEUTRAL",
        "BEARISH",
        "STRONG_BEARISH",
    ] = Field(
        description="기술지표를 기반으로 한 현재 추세"
    )

    signal: Literal[
        "BUY",
        "HOLD",
        "SELL",
    ] = Field(
        description="AI의 참고 매매 의견"
    )

    confidence: int = Field(
        ge=0,
        le=100,
        description="AI 분석 신뢰도 0부터 100"
    )

    risk_level: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
    ] = Field(
        description="현재 기술적 위험 수준"
    )

    positive_factors: list[str] = Field(
        max_length=3,
        description="긍정적인 기술 요인 최대 3개"
    )

    risk_factors: list[str] = Field(
        max_length=3,
        description="위험 기술 요인 최대 3개"
    )

    summary: str = Field(
        max_length=500,
        description="한국어 종합 설명"
    )


class StockScanResult(BaseModel):
    """
    한 종목의 전체 분석 결과입니다.
    """

    symbol: str

    close: float

    technical_score: int

    technical_signal: Literal[
        "BUY",
        "HOLD",
        "SELL",
    ]

    ai_signal: Literal[
        "BUY",
        "HOLD",
        "SELL",
    ]

    ai_confidence: int

    risk_level: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
    ]

    final_score: float

    backtest_return: float

    max_drawdown: float

    win_rate: float

    summary: str