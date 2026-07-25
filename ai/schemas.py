from typing import Literal

from pydantic import BaseModel, Field


class AIStockAnalysis(BaseModel):
    """
    OpenAI가 반환하는 구조화된 기술분석 결과입니다.
    """

    trend: Literal[
        "STRONG_BULLISH",
        "BULLISH",
        "NEUTRAL",
        "BEARISH",
        "STRONG_BEARISH",
    ] = Field(
        description="기술지표를 바탕으로 판단한 현재 추세"
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
        description="AI 분석 신뢰도"
    )

    risk_level: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
    ] = Field(
        description="현재 기술적 위험 수준"
    )

    positive_factors: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="긍정적인 기술 요인"
    )

    risk_factors: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="위험 기술 요인"
    )

    summary: str = Field(
        max_length=500,
        description="한국어 종합 설명"
    )


class StockScanResult(BaseModel):
    """
    한 종목의 전체 스캔 결과입니다.

    포함 내용:
    - 기술분석
    - OpenAI 분석
    - 머신러닝 예측
    - 백테스트
    - Trade Plan
    """

    symbol: str
    close: float

    # --------------------------------------------------------
    # 기술분석
    # --------------------------------------------------------

    technical_score: int

    technical_signal: Literal[
        "BUY",
        "HOLD",
        "SELL",
    ]

    # --------------------------------------------------------
    # OpenAI 분석
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 머신러닝 예측
    # --------------------------------------------------------

    ml_prediction: Literal[
        "BULLISH",
        "NEUTRAL",
        "BEARISH",
        "UNAVAILABLE",
    ]

    ml_up_probability: float
    ml_down_probability: float

    ml_validation_accuracy: float
    ml_balanced_accuracy: float

    ml_model_status: Literal[
        "USABLE",
        "PROMISING",
        "EXPERIMENTAL",
        "WEAK",
        "LOW_DATA",
        "UNAVAILABLE",
    ]

    ml_prediction_date: str
    ml_horizon_days: int
    ml_feature_count: int

    # --------------------------------------------------------
    # 최종점수
    # --------------------------------------------------------

    final_score: float

    # --------------------------------------------------------
    # 백테스트
    # --------------------------------------------------------

    backtest_return: float
    max_drawdown: float
    win_rate: float

    # --------------------------------------------------------
    # Trade Plan
    # --------------------------------------------------------

    plan_status: Literal[
        "ATTRACTIVE",
        "WATCH",
        "WEAK",
        "AVOID",
    ]

    entry_low: float
    entry_high: float

    stop_loss: float
    target_1: float
    target_2: float

    expected_gain_1: float
    expected_gain_2: float
    expected_loss: float

    risk_reward_1: float
    risk_reward_2: float

    atr: float
    volatility_percent: float
    holding_period: str

    summary: str