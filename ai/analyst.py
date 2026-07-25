import math
import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from ai.schemas import AIStockAnalysis
from config import (
    OPENAI_MAX_OUTPUT_TOKENS,
    OPENAI_MODEL,
)


# 프로젝트 최상단의 .env 파일을 읽습니다.
load_dotenv()


def create_client() -> OpenAI:
    """
    .env 파일에서 OpenAI API 키를 불러와
    OpenAI 클라이언트를 생성합니다.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY를 찾을 수 없습니다. "
            "프로젝트 최상단의 .env 파일을 확인하세요."
        )

    return OpenAI(api_key=api_key)


def validate_number(
    name: str,
    value: float,
) -> float:
    """
    값이 정상적인 유한 숫자인지 검사합니다.
    """

    number = float(value)

    if not math.isfinite(number):
        raise ValueError(
            f"{name} 값이 정상적인 숫자가 아닙니다: {value}"
        )

    return number


def normalize_signal(signal: str) -> str:
    """
    신호를 BUY, HOLD, SELL 중 하나로 정리합니다.
    """

    normalized = str(signal).upper().strip()

    if normalized not in {
        "BUY",
        "HOLD",
        "SELL",
    }:
        return "HOLD"

    return normalized


def build_analysis_prompt(
    symbol: str,
    close: float,
    ma5: float,
    ma20: float,
    rsi: float,
    macd: float,
    macd_signal: float,
    macd_hist: float,
    bb_upper: float,
    bb_middle: float,
    bb_lower: float,
    technical_score: int,
    technical_signal: str,
) -> str:
    """
    OpenAI에 전달할 기술분석 프롬프트를 만듭니다.
    """

    return f"""
당신은 주식 기술지표를 해석하는 신중한 분석 보조 도구입니다.

아래에 제공된 기술지표만 사용하세요.

규칙:
- 최신 뉴스나 실적을 알고 있는 것처럼 말하지 마세요.
- 목표주가 또는 미래 가격을 예측하지 마세요.
- 수익을 보장하지 마세요.
- 기술지표가 서로 충돌하면 위험 요소에 명확히 작성하세요.
- 프로그램 신호를 참고하되 무조건 따라 하지 마세요.
- positive_factors, risk_factors, summary는 한국어로 작성하세요.
- positive_factors와 risk_factors는 각각 최대 3개만 작성하세요.
- summary는 짧은 한국어 3문장 이내로 작성하세요.

종목: {symbol}

가격:
- 종가: {close:.2f}

추세:
- MA5: {ma5:.2f}
- MA20: {ma20:.2f}

모멘텀:
- RSI: {rsi:.2f}
- MACD: {macd:.2f}
- MACD Signal: {macd_signal:.2f}
- MACD Histogram: {macd_hist:.2f}

볼린저 밴드:
- Upper: {bb_upper:.2f}
- Middle: {bb_middle:.2f}
- Lower: {bb_lower:.2f}

프로그램 분석:
- 기술 점수: {technical_score}/100
- 기술 신호: {technical_signal}

반드시 지정된 구조에 맞는 결과만 반환하세요.
""".strip()


def create_fallback_analysis(
    technical_signal: str,
    error_message: str,
) -> AIStockAnalysis:
    """
    AI 호출이 실패해도 프로그램이 중단되지 않도록
    기본 분석 결과를 반환합니다.
    """

    return AIStockAnalysis(
        trend="NEUTRAL",
        signal=technical_signal,
        confidence=0,
        risk_level="HIGH",
        positive_factors=[],
        risk_factors=[
            "AI 기술분석을 정상적으로 완료하지 못했습니다.",
            error_message[:200],
        ],
        summary=(
            "AI 분석을 사용할 수 없어 프로그램 기술 신호만 표시합니다. "
            "백테스트와 기술점수 계산 결과를 별도로 확인해야 합니다."
        ),
    )


def analyze_technical_data(
    symbol: str,
    close: float,
    ma5: float,
    ma20: float,
    rsi: float,
    macd: float,
    macd_signal: float,
    macd_hist: float,
    bb_upper: float,
    bb_middle: float,
    bb_lower: float,
    technical_score: int,
    technical_signal: str,
) -> AIStockAnalysis:
    """
    실제 기술지표를 OpenAI에 전달하고
    구조화된 AIStockAnalysis 객체를 반환합니다.
    """

    symbol = str(symbol).upper().strip()

    if not symbol:
        raise ValueError("symbol이 비어 있습니다.")

    close = validate_number("close", close)
    ma5 = validate_number("ma5", ma5)
    ma20 = validate_number("ma20", ma20)
    rsi = validate_number("rsi", rsi)
    macd = validate_number("macd", macd)

    macd_signal = validate_number(
        "macd_signal",
        macd_signal,
    )

    macd_hist = validate_number(
        "macd_hist",
        macd_hist,
    )

    bb_upper = validate_number(
        "bb_upper",
        bb_upper,
    )

    bb_middle = validate_number(
        "bb_middle",
        bb_middle,
    )

    bb_lower = validate_number(
        "bb_lower",
        bb_lower,
    )

    technical_score = max(
        0,
        min(
            100,
            int(technical_score),
        ),
    )

    technical_signal = normalize_signal(
        technical_signal
    )

    prompt = build_analysis_prompt(
        symbol=symbol,
        close=close,
        ma5=ma5,
        ma20=ma20,
        rsi=rsi,
        macd=macd,
        macd_signal=macd_signal,
        macd_hist=macd_hist,
        bb_upper=bb_upper,
        bb_middle=bb_middle,
        bb_lower=bb_lower,
        technical_score=technical_score,
        technical_signal=technical_signal,
    )

    try:
        client = create_client()

        response = client.responses.parse(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "system",
                    "content": (
                        "제공된 기술지표만 분석하고 "
                        "지정된 구조로 응답하세요."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            text_format=AIStockAnalysis,
            max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS,
        )

        if response.status == "incomplete":
            incomplete_details = getattr(
                response,
                "incomplete_details",
                None,
            )

            return create_fallback_analysis(
                technical_signal=technical_signal,
                error_message=(
                    "OpenAI 응답이 완성되지 않았습니다. "
                    f"추가 정보: {incomplete_details}"
                ),
            )

        parsed_result = response.output_parsed

        if parsed_result is None:
            return create_fallback_analysis(
                technical_signal=technical_signal,
                error_message=(
                    "OpenAI 응답에서 구조화된 결과를 "
                    "읽지 못했습니다."
                ),
            )

        return parsed_result

    except ValidationError as error:
        return create_fallback_analysis(
            technical_signal=technical_signal,
            error_message=(
                f"AI 응답 데이터 검증 오류: {error}"
            ),
        )

    except Exception as error:
        return create_fallback_analysis(
            technical_signal=technical_signal,
            error_message=(
                f"{type(error).__name__}: {error}"
            ),
        )