import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from data.market import get_history


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = PROJECT_ROOT / "output"

LATEST_PREDICTION_PATH = (
    OUTPUT_DIRECTORY
    / "daily_prediction_latest.json"
)

RECOMMENDATION_DIRECTORY = (
    OUTPUT_DIRECTORY
    / "recommendations"
)

LATEST_RECOMMENDATION_PATH = (
    OUTPUT_DIRECTORY
    / "recommendation_latest.json"
)


@dataclass
class RecommendationResult:
    """
    한 종목의 V6.0 매매 참고 계획입니다.
    """

    symbol: str
    success: bool

    generated_at: str
    market_data_date: str | None

    recommendation: str
    stars: int
    score: float

    prediction: str
    up_probability: float
    down_probability: float
    confidence: float
    action_signal: str

    current_price: float

    entry_low: float
    entry_high: float

    stop_loss: float

    target_1: float
    target_2: float

    expected_loss_percent: float
    expected_gain_1_percent: float
    expected_gain_2_percent: float

    risk_reward_1: float
    risk_reward_2: float

    atr: float
    atr_percent: float
    volatility_level: str

    suggested_position_percent: float

    reasons: list[str]
    warnings: list[str]

    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ensure_output_directories() -> None:
    """
    추천 결과 저장 폴더를 생성합니다.
    """

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    RECOMMENDATION_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    값을 안전하게 float로 변환합니다.
    """

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def normalize_symbol(
    symbol: Any,
) -> str:
    """
    종목 코드를 대문자로 정리합니다.
    """

    normalized = (
        str(symbol or "")
        .upper()
        .strip()
    )

    if not normalized:
        raise ValueError(
            "종목 코드가 비어 있습니다."
        )

    return normalized


def normalize_prediction(
    prediction: Any,
) -> str:
    """
    예측 방향을 표준 형식으로 변환합니다.
    """

    normalized = (
        str(prediction or "NEUTRAL")
        .upper()
        .strip()
    )

    if normalized in {
        "BULLISH",
        "BUY",
        "UP",
        "POSITIVE",
    }:
        return "BULLISH"

    if normalized in {
        "BEARISH",
        "SELL",
        "DOWN",
        "NEGATIVE",
    }:
        return "BEARISH"

    return "NEUTRAL"


def normalize_action_signal(
    signal: Any,
) -> str:
    """
    저장된 행동 신호를 표준화합니다.
    """

    normalized = (
        str(signal or "HOLD")
        .upper()
        .strip()
    )

    valid_signals = {
        "STRONG_BUY",
        "BUY",
        "WATCH_BUY",
        "HOLD",
        "WAIT",
        "SELL",
        "AVOID",
    }

    if normalized in valid_signals:
        return normalized

    return "HOLD"


def load_latest_prediction_report() -> dict[str, Any]:
    """
    V5.2 일일 예측 최신 JSON을 읽습니다.
    """

    if not LATEST_PREDICTION_PATH.exists():
        raise FileNotFoundError(
            "daily_prediction_latest.json이 없습니다. "
            "먼저 Daily Pipeline을 실행하세요."
        )

    with LATEST_PREDICTION_PATH.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        report = json.load(
            file
        )

    if not isinstance(
        report,
        dict,
    ):
        raise ValueError(
            "일일 예측 JSON 형식이 올바르지 않습니다."
        )

    predictions = report.get(
        "predictions"
    )

    if not isinstance(
        predictions,
        list,
    ):
        raise ValueError(
            "예측 JSON에서 predictions 목록을 "
            "찾지 못했습니다."
        )

    return report


def prepare_market_data(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    가격 데이터와 ATR을 계산합니다.
    """

    if data is None or data.empty:
        raise ValueError(
            "시장 데이터가 비어 있습니다."
        )

    required_columns = {
        "High",
        "Low",
        "Close",
    }

    missing_columns = (
        required_columns
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "시장 데이터에 필요한 열이 없습니다: "
            f"{sorted(missing_columns)}"
        )

    prepared = data.copy()

    for column in (
        "High",
        "Low",
        "Close",
    ):
        prepared[column] = pd.to_numeric(
            prepared[column],
            errors="coerce",
        )

    prepared["PREVIOUS_CLOSE"] = (
        prepared["Close"].shift(1)
    )

    prepared["TR_HIGH_LOW"] = (
        prepared["High"]
        - prepared["Low"]
    ).abs()

    prepared["TR_HIGH_PREVIOUS"] = (
        prepared["High"]
        - prepared["PREVIOUS_CLOSE"]
    ).abs()

    prepared["TR_LOW_PREVIOUS"] = (
        prepared["Low"]
        - prepared["PREVIOUS_CLOSE"]
    ).abs()

    prepared["TRUE_RANGE"] = prepared[
        [
            "TR_HIGH_LOW",
            "TR_HIGH_PREVIOUS",
            "TR_LOW_PREVIOUS",
        ]
    ].max(
        axis=1
    )

    prepared["ATR14"] = (
        prepared["TRUE_RANGE"]
        .rolling(
            window=14,
            min_periods=14,
        )
        .mean()
    )

    prepared = prepared.dropna(
        subset=[
            "Close",
            "ATR14",
        ]
    )

    if prepared.empty:
        raise ValueError(
            "ATR 계산에 필요한 데이터가 부족합니다."
        )

    return prepared


def get_volatility_level(
    atr_percent: float,
) -> str:
    """
    ATR 비율을 이용해 변동성 수준을 결정합니다.
    """

    if atr_percent < 1.5:
        return "LOW"

    if atr_percent < 3.0:
        return "MEDIUM"

    if atr_percent < 5.0:
        return "HIGH"

    return "VERY_HIGH"


def calculate_recommendation_score(
    prediction: str,
    up_probability: float,
    confidence: float,
    action_signal: str,
    volatility_level: str,
) -> tuple[float, list[str]]:
    """
    머신러닝 예측, 확률, 신뢰도,
    행동 신호 및 변동성을 결합합니다.
    """

    score = 50.0
    reasons: list[str] = []

    if prediction == "BULLISH":
        score += 18.0
        reasons.append(
            "머신러닝 예측 방향이 BULLISH입니다."
        )

    elif prediction == "BEARISH":
        score -= 22.0
        reasons.append(
            "머신러닝 예측 방향이 BEARISH입니다."
        )

    else:
        reasons.append(
            "머신러닝 예측 방향이 NEUTRAL입니다."
        )

    probability_adjustment = (
        up_probability - 50.0
    ) * 0.6

    score += probability_adjustment

    if up_probability >= 70.0:
        reasons.append(
            f"상승 확률이 {up_probability:.2f}%로 높습니다."
        )

    elif up_probability >= 58.0:
        reasons.append(
            f"상승 확률이 {up_probability:.2f}%로 "
            "보통 이상입니다."
        )

    elif up_probability <= 40.0:
        reasons.append(
            f"상승 확률이 {up_probability:.2f}%로 낮습니다."
        )

    if confidence >= 50.0:
        score += 8.0
        reasons.append(
            f"방향성 신뢰도 차이가 {confidence:.2f}%입니다."
        )

    elif confidence >= 20.0:
        score += 3.0
        reasons.append(
            f"방향성 신뢰도는 {confidence:.2f}%입니다."
        )

    else:
        score -= 5.0
        reasons.append(
            f"방향성 신뢰도가 {confidence:.2f}%로 낮습니다."
        )

    signal_adjustments = {
        "STRONG_BUY": 14.0,
        "BUY": 10.0,
        "WATCH_BUY": 5.0,
        "HOLD": 0.0,
        "WAIT": -3.0,
        "SELL": -15.0,
        "AVOID": -20.0,
    }

    score += signal_adjustments.get(
        action_signal,
        0.0,
    )

    reasons.append(
        f"기존 행동 신호는 {action_signal}입니다."
    )

    if volatility_level == "HIGH":
        score -= 4.0
        reasons.append(
            "가격 변동성이 높아 점수를 낮췄습니다."
        )

    elif volatility_level == "VERY_HIGH":
        score -= 10.0
        reasons.append(
            "가격 변동성이 매우 높아 위험 점수를 "
            "크게 반영했습니다."
        )

    return (
        max(
            0.0,
            min(
                100.0,
                score,
            ),
        ),
        reasons,
    )


def score_to_recommendation(
    score: float,
    prediction: str,
) -> tuple[str, int]:
    """
    점수를 추천 등급과 별 개수로 변환합니다.
    """

    if (
        score >= 82.0
        and prediction == "BULLISH"
    ):
        return "STRONG_BUY", 5

    if (
        score >= 68.0
        and prediction != "BEARISH"
    ):
        return "BUY", 4

    if (
        score >= 55.0
        and prediction != "BEARISH"
    ):
        return "WATCH_BUY", 3

    if score >= 42.0:
        return "HOLD", 2

    return "AVOID", 1


def calculate_position_percent(
    recommendation: str,
    volatility_level: str,
    confidence: float,
) -> float:
    """
    추천 등급과 변동성에 따라
    참고 포지션 비율을 계산합니다.
    """

    base_percent = {
        "STRONG_BUY": 10.0,
        "BUY": 7.0,
        "WATCH_BUY": 4.0,
        "HOLD": 0.0,
        "AVOID": 0.0,
    }.get(
        recommendation,
        0.0,
    )

    volatility_multiplier = {
        "LOW": 1.0,
        "MEDIUM": 0.85,
        "HIGH": 0.60,
        "VERY_HIGH": 0.35,
    }.get(
        volatility_level,
        0.60,
    )

    confidence_multiplier = 1.0

    if confidence < 15.0:
        confidence_multiplier = 0.50

    elif confidence < 30.0:
        confidence_multiplier = 0.75

    result = (
        base_percent
        * volatility_multiplier
        * confidence_multiplier
    )

    return round(
        result,
        2,
    )


def create_failed_result(
    symbol: str,
    error: Exception,
) -> RecommendationResult:
    """
    개별 종목 실패 결과를 생성합니다.
    """

    return RecommendationResult(
        symbol=symbol,
        success=False,

        generated_at=datetime.now().isoformat(),
        market_data_date=None,

        recommendation="ERROR",
        stars=0,
        score=0.0,

        prediction="UNKNOWN",
        up_probability=0.0,
        down_probability=0.0,
        confidence=0.0,
        action_signal="UNKNOWN",

        current_price=0.0,

        entry_low=0.0,
        entry_high=0.0,

        stop_loss=0.0,

        target_1=0.0,
        target_2=0.0,

        expected_loss_percent=0.0,
        expected_gain_1_percent=0.0,
        expected_gain_2_percent=0.0,

        risk_reward_1=0.0,
        risk_reward_2=0.0,

        atr=0.0,
        atr_percent=0.0,
        volatility_level="UNKNOWN",

        suggested_position_percent=0.0,

        reasons=[],

        warnings=[
            "추천 결과를 생성하지 못했습니다."
        ],

        error_type=type(error).__name__,
        error_message=str(error),
    )


def create_stock_recommendation(
    prediction_record: dict[str, Any],
    period: str = "6mo",
    interval: str = "1d",
) -> RecommendationResult:
    """
    한 종목의 V6.0 추천 결과를 생성합니다.
    """

    symbol = normalize_symbol(
        prediction_record.get(
            "symbol"
        )
    )

    try:
        if not prediction_record.get(
            "success",
            False,
        ):
            raise ValueError(
                "성공한 일일 예측 레코드가 아닙니다."
            )

        prediction = normalize_prediction(
            prediction_record.get(
                "prediction"
            )
        )

        up_probability = safe_float(
            prediction_record.get(
                "up_probability"
            )
        )

        down_probability = safe_float(
            prediction_record.get(
                "down_probability"
            )
        )

        confidence = safe_float(
            prediction_record.get(
                "confidence"
            )
        )

        action_signal = (
            normalize_action_signal(
                prediction_record.get(
                    "action_signal"
                )
            )
        )

        data = get_history(
            symbol=symbol,
            period=period,
            interval=interval,
        )

        prepared = prepare_market_data(
            data
        )

        latest_row = prepared.iloc[-1]

        current_price = safe_float(
            latest_row["Close"]
        )

        atr = safe_float(
            latest_row["ATR14"]
        )

        if current_price <= 0:
            raise ValueError(
                "현재 가격이 올바르지 않습니다."
            )

        if atr <= 0:
            raise ValueError(
                "ATR 값이 올바르지 않습니다."
            )

        atr_percent = (
            atr
            / current_price
        ) * 100.0

        volatility_level = (
            get_volatility_level(
                atr_percent
            )
        )

        score, reasons = (
            calculate_recommendation_score(
                prediction=prediction,
                up_probability=(
                    up_probability
                ),
                confidence=confidence,
                action_signal=(
                    action_signal
                ),
                volatility_level=(
                    volatility_level
                ),
            )
        )

        recommendation, stars = (
            score_to_recommendation(
                score=score,
                prediction=prediction,
            )
        )

        # 현재가에서 최대 약 0.4 ATR 아래까지
        # 진입 후보 구간으로 사용합니다.
        entry_high = current_price

        entry_low = max(
            0.01,
            current_price
            - (
                atr * 0.40
            ),
        )

        reference_entry = (
            entry_low
            + entry_high
        ) / 2.0

        # 손절가는 진입 기준가에서 1.5 ATR 아래
        stop_loss = max(
            0.01,
            reference_entry
            - (
                atr * 1.50
            ),
        )

        risk_per_share = (
            reference_entry
            - stop_loss
        )

        # 목표가는 위험의 1.5배와 2.5배
        target_1 = (
            reference_entry
            + (
                risk_per_share
                * 1.50
            )
        )

        target_2 = (
            reference_entry
            + (
                risk_per_share
                * 2.50
            )
        )

        expected_loss_percent = (
            risk_per_share
            / reference_entry
        ) * 100.0

        expected_gain_1_percent = (
            (
                target_1
                - reference_entry
            )
            / reference_entry
        ) * 100.0

        expected_gain_2_percent = (
            (
                target_2
                - reference_entry
            )
            / reference_entry
        ) * 100.0

        risk_reward_1 = 0.0
        risk_reward_2 = 0.0

        if risk_per_share > 0:
            risk_reward_1 = (
                target_1
                - reference_entry
            ) / risk_per_share

            risk_reward_2 = (
                target_2
                - reference_entry
            ) / risk_per_share

        suggested_position_percent = (
            calculate_position_percent(
                recommendation=(
                    recommendation
                ),
                volatility_level=(
                    volatility_level
                ),
                confidence=confidence,
            )
        )

        warnings: list[str] = [
            "이 결과는 실제 주문 지시가 아니라 "
            "기술적·통계적 참고 계산입니다."
        ]

        if confidence < 20.0:
            warnings.append(
                "상승과 하락 확률 차이가 작아 "
                "방향성이 약합니다."
            )

        if volatility_level in {
            "HIGH",
            "VERY_HIGH",
        }:
            warnings.append(
                "변동성이 높아 손절 체결 및 "
                "가격 갭 위험이 커질 수 있습니다."
            )

        if recommendation in {
            "HOLD",
            "AVOID",
        }:
            warnings.append(
                "현재 추천 등급에서는 신규 진입을 "
                "적극적으로 제안하지 않습니다."
            )

        market_data_date = (
            pd.Timestamp(
                prepared.index[-1]
            ).strftime(
                "%Y-%m-%d"
            )
        )

        return RecommendationResult(
            symbol=symbol,
            success=True,

            generated_at=(
                datetime.now().isoformat()
            ),

            market_data_date=(
                market_data_date
            ),

            recommendation=(
                recommendation
            ),

            stars=stars,

            score=round(
                score,
                2,
            ),

            prediction=prediction,

            up_probability=round(
                up_probability,
                2,
            ),

            down_probability=round(
                down_probability,
                2,
            ),

            confidence=round(
                confidence,
                2,
            ),

            action_signal=(
                action_signal
            ),

            current_price=round(
                current_price,
                2,
            ),

            entry_low=round(
                entry_low,
                2,
            ),

            entry_high=round(
                entry_high,
                2,
            ),

            stop_loss=round(
                stop_loss,
                2,
            ),

            target_1=round(
                target_1,
                2,
            ),

            target_2=round(
                target_2,
                2,
            ),

            expected_loss_percent=round(
                expected_loss_percent,
                2,
            ),

            expected_gain_1_percent=round(
                expected_gain_1_percent,
                2,
            ),

            expected_gain_2_percent=round(
                expected_gain_2_percent,
                2,
            ),

            risk_reward_1=round(
                risk_reward_1,
                2,
            ),

            risk_reward_2=round(
                risk_reward_2,
                2,
            ),

            atr=round(
                atr,
                2,
            ),

            atr_percent=round(
                atr_percent,
                2,
            ),

            volatility_level=(
                volatility_level
            ),

            suggested_position_percent=(
                suggested_position_percent
            ),

            reasons=reasons,
            warnings=warnings,
        )

    except Exception as error:
        return create_failed_result(
            symbol=symbol,
            error=error,
        )


def save_recommendation_report(
    report: dict[str, Any],
) -> tuple[Path, Path]:
    """
    시간별 JSON과 latest JSON을 저장합니다.
    """

    ensure_output_directories()

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    dated_path = (
        RECOMMENDATION_DIRECTORY
        / f"recommendation_{timestamp}.json"
    )

    for path in (
        dated_path,
        LATEST_RECOMMENDATION_PATH,
    ):
        with path.open(
            mode="w",
            encoding="utf-8",
        ) as file:
            json.dump(
                report,
                file,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

    return (
        dated_path,
        LATEST_RECOMMENDATION_PATH,
    )


def print_recommendation(
    result: RecommendationResult,
) -> None:
    """
    종목별 추천 결과를 출력합니다.
    """

    print()
    print("-" * 72)
    print(
        f"{result.symbol} V6.0 RECOMMENDATION"
    )
    print("-" * 72)

    if not result.success:
        print(
            f"Status        : ERROR"
        )

        print(
            f"Error type    : "
            f"{result.error_type}"
        )

        print(
            f"Error message : "
            f"{result.error_message}"
        )

        return

    star_text = (
        "★" * result.stars
        + "☆" * (
            5 - result.stars
        )
    )

    print(
        f"Recommendation : "
        f"{star_text} "
        f"{result.recommendation}"
    )

    print(
        f"Score          : "
        f"{result.score:.2f}/100"
    )

    print(
        f"Prediction     : "
        f"{result.prediction}"
    )

    print(
        f"Up probability : "
        f"{result.up_probability:.2f}%"
    )

    print(
        f"Confidence     : "
        f"{result.confidence:.2f}%"
    )

    print(
        f"Current price  : "
        f"${result.current_price:,.2f}"
    )

    print(
        f"Entry zone     : "
        f"${result.entry_low:,.2f} "
        f"- ${result.entry_high:,.2f}"
    )

    print(
        f"Stop loss      : "
        f"${result.stop_loss:,.2f}"
    )

    print(
        f"Target 1       : "
        f"${result.target_1:,.2f} "
        f"({result.expected_gain_1_percent:.2f}%)"
    )

    print(
        f"Target 2       : "
        f"${result.target_2:,.2f} "
        f"({result.expected_gain_2_percent:.2f}%)"
    )

    print(
        f"Risk/Reward 1  : "
        f"1:{result.risk_reward_1:.2f}"
    )

    print(
        f"Risk/Reward 2  : "
        f"1:{result.risk_reward_2:.2f}"
    )

    print(
        f"ATR            : "
        f"${result.atr:,.2f} "
        f"({result.atr_percent:.2f}%)"
    )

    print(
        f"Volatility     : "
        f"{result.volatility_level}"
    )

    print(
        f"Position guide : "
        f"{result.suggested_position_percent:.2f}%"
    )

    print()
    print("Reasons:")

    for reason in result.reasons:
        print(
            f"- {reason}"
        )

    print()
    print("Warnings:")

    for warning in result.warnings:
        print(
            f"- {warning}"
        )


def generate_recommendations() -> dict[str, Any]:
    """
    최신 성공 예측 전체에 대해
    V6.0 추천 결과를 생성합니다.
    """

    latest_report = (
        load_latest_prediction_report()
    )

    predictions = latest_report.get(
        "predictions",
        [],
    )

    results: list[
        RecommendationResult
    ] = []

    for prediction_record in predictions:
        if not isinstance(
            prediction_record,
            dict,
        ):
            continue

        symbol = str(
            prediction_record.get(
                "symbol",
                "UNKNOWN",
            )
        ).upper()

        if not prediction_record.get(
            "success",
            False,
        ):
            print()
            print(
                f"{symbol}: 성공한 저장 모델 예측이 없어 "
                "추천 계산에서 제외합니다."
            )

            continue

        result = create_stock_recommendation(
            prediction_record=(
                prediction_record
            )
        )

        results.append(
            result
        )

        print_recommendation(
            result
        )

    successful_results = [
        result
        for result in results
        if result.success
    ]

    failed_results = [
        result
        for result in results
        if not result.success
    ]

    ranked_results = sorted(
        successful_results,
        key=lambda item: item.score,
        reverse=True,
    )

    recommendation_counts = {
        "STRONG_BUY": 0,
        "BUY": 0,
        "WATCH_BUY": 0,
        "HOLD": 0,
        "AVOID": 0,
    }

    for result in successful_results:
        recommendation_counts[
            result.recommendation
        ] = (
            recommendation_counts.get(
                result.recommendation,
                0,
            )
            + 1
        )

    top_result = (
        ranked_results[0]
        if ranked_results
        else None
    )

    report: dict[str, Any] = {
        "version": "V6.0",

        "generated_at": (
            datetime.now().isoformat()
        ),

        "summary": {
            "total_results": len(
                results
            ),

            "successful_count": len(
                successful_results
            ),

            "failed_count": len(
                failed_results
            ),

            "recommendation_counts": (
                recommendation_counts
            ),

            "top_symbol": (
                top_result.symbol
                if top_result
                else None
            ),

            "top_recommendation": (
                top_result.recommendation
                if top_result
                else None
            ),

            "top_score": (
                top_result.score
                if top_result
                else None
            ),
        },

        "recommendations": [
            result.to_dict()
            for result in ranked_results
        ],

        "failed_results": [
            result.to_dict()
            for result in failed_results
        ],

        "disclaimer": (
            "This report is an experimental technical and "
            "statistical reference, not investment advice "
            "or a guarantee of returns."
        ),
    }

    (
        report_path,
        latest_path,
    ) = save_recommendation_report(
        report
    )

    report["files"] = {
        "report_path": str(
            report_path
        ),

        "latest_path": str(
            latest_path
        ),
    }

    # files 경로를 포함한 최종 내용으로 다시 저장합니다.
    for path in (
        report_path,
        latest_path,
    ):
        with path.open(
            mode="w",
            encoding="utf-8",
        ) as file:
            json.dump(
                report,
                file,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

    print()
    print("=" * 72)
    print(
        "AI STOCK BOT V6.0 "
        "RECOMMENDATION SUMMARY"
    )
    print("=" * 72)

    print(
        f"Successful      : "
        f"{len(successful_results)}"
    )

    print(
        f"Failed          : "
        f"{len(failed_results)}"
    )

    if top_result:
        print(
            f"Top symbol      : "
            f"{top_result.symbol}"
        )

        print(
            f"Top rating      : "
            f"{top_result.recommendation}"
        )

        print(
            f"Top score       : "
            f"{top_result.score:.2f}/100"
        )

    print(
        f"Report          : "
        f"{report_path}"
    )

    print(
        f"Latest report   : "
        f"{latest_path}"
    )

    print("=" * 72)

    return report