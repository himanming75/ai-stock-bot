import csv
import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from data.market import get_history
from ml.model_registry import active_model_exists
from ml.model_trainer import predict_with_saved_model


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = PROJECT_ROOT / "output"
PREDICTION_DIRECTORY = OUTPUT_DIRECTORY / "predictions"


@dataclass
class DailyPredictionResult:
    """
    한 종목의 일일 머신러닝 예측 결과입니다.
    """

    symbol: str
    success: bool

    generated_at: str
    market_data_date: str | None

    model_name: str | None
    model_created_at: str | None
    model_status: str | None

    latest_close: float | None
    prediction_horizon: int | None

    prediction: str
    up_probability: float
    down_probability: float

    confidence: float
    confidence_level: str

    action_signal: str
    reason: str

    error_type: str | None
    error_message: str | None

    def to_dict(self) -> dict[str, Any]:
        """
        결과를 dictionary로 변환합니다.
        """

        return asdict(self)


def normalize_symbol(
    symbol: str,
) -> str:
    """
    종목 코드를 대문자로 정리합니다.
    """

    normalized = (
        str(symbol)
        .upper()
        .strip()
    )

    if not normalized:
        raise ValueError(
            "종목 코드가 비어 있습니다."
        )

    return normalized


def normalize_symbols(
    symbols: list[str],
) -> list[str]:
    """
    빈 종목과 중복 종목을 제거합니다.
    """

    cleaned_symbols: list[str] = []

    for symbol in symbols:
        normalized = (
            str(symbol)
            .upper()
            .strip()
        )

        if not normalized:
            continue

        if normalized not in cleaned_symbols:
            cleaned_symbols.append(
                normalized
            )

    return cleaned_symbols


def ensure_output_directories() -> None:
    """
    결과 저장 폴더를 생성합니다.
    """

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    PREDICTION_DIRECTORY.mkdir(
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


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    """
    값을 안전하게 int로 변환합니다.
    """

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def object_to_dict(
    value: Any,
) -> dict[str, Any]:
    """
    dataclass, dictionary 또는 일반 객체를
    dictionary 형태로 변환합니다.
    """

    if value is None:
        return {}

    if isinstance(value, dict):
        return value.copy()

    if is_dataclass(value):
        return asdict(value)

    if hasattr(value, "to_dict"):
        converted = value.to_dict()

        if isinstance(converted, dict):
            return converted

    if hasattr(value, "__dict__"):
        return dict(value.__dict__)

    return {}


def get_first_value(
    data: dict[str, Any],
    names: list[str],
    default: Any = None,
) -> Any:
    """
    여러 후보 키 중 존재하는 첫 번째 값을 반환합니다.

    기존 코드의 필드 이름이 약간 달라도
    작동하도록 만든 호환 기능입니다.
    """

    for name in names:
        if name in data:
            value = data[name]

            if value is not None:
                return value

    return default


def normalize_probability(
    value: Any,
) -> float:
    """
    확률을 0~100 범위로 정리합니다.

    저장 모델이 0.55를 반환하면 55%로,
    55.0을 반환하면 그대로 55%로 처리합니다.
    """

    probability = safe_float(
        value,
        default=0.0,
    )

    if 0.0 <= probability <= 1.0:
        probability *= 100.0

    return round(
        max(
            0.0,
            min(
                probability,
                100.0,
            ),
        ),
        2,
    )


def calculate_confidence(
    up_probability: float,
    down_probability: float,
) -> float:
    """
    50% 중립선에서 얼마나 멀리 떨어졌는지를
    0~100 신뢰도 점수로 환산합니다.

    예:
    상승 확률 50% → 신뢰도 0
    상승 확률 75% → 신뢰도 50
    상승 확률 100% → 신뢰도 100
    """

    strongest_probability = max(
        up_probability,
        down_probability,
    )

    confidence = (
        strongest_probability - 50.0
    ) * 2.0

    return round(
        max(
            0.0,
            min(
                confidence,
                100.0,
            ),
        ),
        2,
    )


def determine_confidence_level(
    confidence: float,
) -> str:
    """
    숫자 신뢰도를 텍스트 등급으로 변환합니다.
    """

    if confidence >= 70.0:
        return "HIGH"

    if confidence >= 40.0:
        return "MEDIUM"

    return "LOW"


def normalize_prediction(
    prediction: Any,
    up_probability: float,
) -> str:
    """
    모델의 예측 문자열을 표준화합니다.
    """

    normalized = (
        str(prediction or "")
        .upper()
        .strip()
    )

    bullish_values = {
        "BULLISH",
        "BUY",
        "UP",
        "POSITIVE",
        "1",
    }

    bearish_values = {
        "BEARISH",
        "SELL",
        "DOWN",
        "NEGATIVE",
        "0",
    }

    if normalized in bullish_values:
        return "BULLISH"

    if normalized in bearish_values:
        return "BEARISH"

    if normalized == "NEUTRAL":
        return "NEUTRAL"

    # 예측 문자열을 알 수 없을 때
    # 확률로 다시 판정합니다.
    if up_probability >= 60.0:
        return "BULLISH"

    if up_probability <= 40.0:
        return "BEARISH"

    return "NEUTRAL"


def create_action_signal(
    prediction: str,
    up_probability: float,
    confidence_level: str,
    model_status: str | None,
) -> tuple[str, str]:
    """
    머신러닝 예측을 참고 행동 신호로 변환합니다.

    이 신호는 실제 주문 신호가 아니라
    추가 검토를 위한 참고 분류입니다.
    """

    normalized_status = (
        str(model_status or "")
        .upper()
        .strip()
    )

    weak_statuses = {
        "WEAK",
        "RESEARCH_ONLY",
        "FAILED",
        "UNRELIABLE",
    }

    if normalized_status in weak_statuses:
        return (
            "HOLD",
            (
                "모델 검증 상태가 낮아 방향 예측보다 "
                "관망과 추가 확인이 우선입니다."
            ),
        )

    if (
        prediction == "BULLISH"
        and up_probability >= 65.0
        and confidence_level in {
            "MEDIUM",
            "HIGH",
        }
    ):
        return (
            "WATCH_BUY",
            (
                "상승 확률과 방향성이 비교적 강합니다. "
                "기술지표와 진입 가격을 추가로 확인하세요."
            ),
        )

    if (
        prediction == "BEARISH"
        and up_probability <= 35.0
        and confidence_level in {
            "MEDIUM",
            "HIGH",
        }
    ):
        return (
            "AVOID",
            (
                "하락 방향 확률이 비교적 강합니다. "
                "신규 진입을 보류하고 위험을 확인하세요."
            ),
        )

    return (
        "HOLD",
        (
            "상승과 하락 확률 차이가 충분히 크지 않아 "
            "명확한 방향성이 확인되지 않습니다."
        ),
    )


def extract_prediction_result(
    symbol: str,
    raw_prediction: Any,
    market_data_date: str | None,
) -> DailyPredictionResult:
    """
    저장 모델의 예측 객체에서 필요한 값을 추출합니다.
    """

    data = object_to_dict(
        raw_prediction
    )

    model_name = get_first_value(
        data,
        [
            "model_name",
            "model",
            "selected_model",
        ],
    )

    model_created_at = get_first_value(
        data,
        [
            "model_created",
            "model_created_at",
            "created_at",
        ],
    )

    model_status = get_first_value(
        data,
        [
            "model_status",
            "selection_status",
            "status",
        ],
    )

    latest_close_value = get_first_value(
        data,
        [
            "latest_close",
            "close",
            "current_price",
        ],
    )

    prediction_horizon_value = get_first_value(
        data,
        [
            "prediction_horizon",
            "horizon_days",
            "prediction_horizon_days",
        ],
        default=5,
    )

    prediction_value = get_first_value(
        data,
        [
            "prediction",
            "latest_prediction",
            "selected_prediction",
        ],
        default="NEUTRAL",
    )

    up_probability_value = get_first_value(
        data,
        [
            "up_probability",
            "upward_probability",
            "latest_up_probability",
            "latest_upward_probability",
            "probability_up",
        ],
        default=50.0,
    )

    down_probability_value = get_first_value(
        data,
        [
            "down_probability",
            "downward_probability",
            "latest_down_probability",
            "probability_down",
        ],
        default=None,
    )

    up_probability = normalize_probability(
        up_probability_value
    )

    if down_probability_value is None:
        down_probability = round(
            100.0 - up_probability,
            2,
        )

    else:
        down_probability = normalize_probability(
            down_probability_value
        )

    probability_total = (
        up_probability
        + down_probability
    )

    # 두 확률의 합이 100이 아닌 경우
    # 비율을 다시 맞춥니다.
    if (
        probability_total > 0
        and abs(
            probability_total - 100.0
        ) > 0.20
    ):
        up_probability = round(
            (
                up_probability
                / probability_total
            )
            * 100.0,
            2,
        )

        down_probability = round(
            100.0 - up_probability,
            2,
        )

    prediction = normalize_prediction(
        prediction=prediction_value,
        up_probability=up_probability,
    )

    confidence = calculate_confidence(
        up_probability=up_probability,
        down_probability=down_probability,
    )

    confidence_level = (
        determine_confidence_level(
            confidence
        )
    )

    (
        action_signal,
        reason,
    ) = create_action_signal(
        prediction=prediction,
        up_probability=up_probability,
        confidence_level=confidence_level,
        model_status=(
            str(model_status)
            if model_status is not None
            else None
        ),
    )

    latest_close = None

    if latest_close_value is not None:
        latest_close = round(
            safe_float(
                latest_close_value
            ),
            2,
        )

    prediction_horizon = safe_int(
        prediction_horizon_value,
        default=5,
    )

    return DailyPredictionResult(
        symbol=normalize_symbol(
            symbol
        ),

        success=True,

        generated_at=(
            datetime.now().isoformat()
        ),

        market_data_date=(
            market_data_date
        ),

        model_name=(
            str(model_name)
            if model_name is not None
            else None
        ),

        model_created_at=(
            str(model_created_at)
            if model_created_at is not None
            else None
        ),

        model_status=(
            str(model_status)
            if model_status is not None
            else None
        ),

        latest_close=latest_close,

        prediction_horizon=(
            prediction_horizon
        ),

        prediction=prediction,

        up_probability=(
            up_probability
        ),

        down_probability=(
            down_probability
        ),

        confidence=confidence,

        confidence_level=(
            confidence_level
        ),

        action_signal=(
            action_signal
        ),

        reason=reason,

        error_type=None,
        error_message=None,
    )


def create_failed_prediction(
    symbol: str,
    error: Exception,
) -> DailyPredictionResult:
    """
    예측 실패 결과를 생성합니다.
    """

    return DailyPredictionResult(
        symbol=normalize_symbol(
            symbol
        ),

        success=False,

        generated_at=(
            datetime.now().isoformat()
        ),

        market_data_date=None,

        model_name=None,
        model_created_at=None,
        model_status=None,

        latest_close=None,
        prediction_horizon=None,

        prediction="ERROR",

        up_probability=0.0,
        down_probability=0.0,

        confidence=0.0,
        confidence_level="NONE",

        action_signal="ERROR",

        reason=(
            "저장된 모델 예측을 완료하지 못했습니다."
        ),

        error_type=(
            type(error).__name__
        ),

        error_message=str(
            error
        ),
    )


def predict_symbol_daily(
    symbol: str,
    period: str = "5y",
    interval: str = "1d",
) -> DailyPredictionResult:
    """
    한 종목의 저장 모델을 불러와
    최신 예측을 생성합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    print()
    print("=" * 78)
    print(
        f"DAILY PREDICTION "
        f"{normalized_symbol} V5.2"
    )
    print("=" * 78)

    if not active_model_exists(
        normalized_symbol
    ):
        raise FileNotFoundError(
            f"{normalized_symbol}의 저장된 운영 모델이 없습니다."
        )

    print(
        "Downloading latest market data..."
    )

    data = get_history(
        symbol=normalized_symbol,
        period=period,
        interval=interval,
    )

    if data is None or data.empty:
        raise ValueError(
            f"{normalized_symbol} 시장 데이터를 "
            "다운로드하지 못했습니다."
        )

    market_data_date = None

    try:
        market_data_date = (
            data.index[-1]
            .strftime("%Y-%m-%d")
        )

    except (
        AttributeError,
        IndexError,
    ):
        market_data_date = str(
            data.index[-1]
        )

    print(
        f"Market data date    : "
        f"{market_data_date}"
    )

    print(
        f"Downloaded rows     : "
        f"{len(data)}"
    )

    print(
        "Running saved model prediction..."
    )

    raw_prediction = (
        predict_with_saved_model(
            symbol=normalized_symbol,
            data=data,
        )
    )

    result = extract_prediction_result(
        symbol=normalized_symbol,
        raw_prediction=raw_prediction,
        market_data_date=market_data_date,
    )

    print()
    print(
        f"Model               : "
        f"{result.model_name or 'N/A'}"
    )

    print(
        f"Model status        : "
        f"{result.model_status or 'N/A'}"
    )

    print(
        f"Latest close        : "
        f"${result.latest_close:,.2f}"
        if result.latest_close is not None
        else "Latest close        : N/A"
    )

    print(
        f"Prediction          : "
        f"{result.prediction}"
    )

    print(
        f"Up probability      : "
        f"{result.up_probability:.2f}%"
    )

    print(
        f"Down probability    : "
        f"{result.down_probability:.2f}%"
    )

    print(
        f"Confidence          : "
        f"{result.confidence:.2f}% "
        f"({result.confidence_level})"
    )

    print(
        f"Reference signal    : "
        f"{result.action_signal}"
    )

    print(
        f"Reason              : "
        f"{result.reason}"
    )

    print("=" * 78)

    return result


def save_json_report(
    report: dict[str, Any],
    dated_path: Path,
    latest_path: Path,
) -> None:
    """
    JSON 보고서를 날짜 파일과 latest 파일에 저장합니다.
    """

    for path in (
        dated_path,
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


def save_csv_report(
    predictions: list[DailyPredictionResult],
    dated_path: Path,
    latest_path: Path,
) -> None:
    """
    CSV 보고서를 날짜 파일과 latest 파일에 저장합니다.
    """

    fieldnames = [
        "symbol",
        "success",
        "generated_at",
        "market_data_date",
        "model_name",
        "model_created_at",
        "model_status",
        "latest_close",
        "prediction_horizon",
        "prediction",
        "up_probability",
        "down_probability",
        "confidence",
        "confidence_level",
        "action_signal",
        "reason",
        "error_type",
        "error_message",
    ]

    for path in (
        dated_path,
        latest_path,
    ):
        with path.open(
            mode="w",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for result in predictions:
                writer.writerow(
                    result.to_dict()
                )


def generate_daily_predictions(
    symbols: list[str],
    period: str = "5y",
    interval: str = "1d",
    continue_on_error: bool = True,
    save_reports: bool = True,
) -> dict[str, Any]:
    """
    여러 종목의 일일 예측을 생성합니다.
    """

    cleaned_symbols = normalize_symbols(
        symbols
    )

    if not cleaned_symbols:
        raise ValueError(
            "예측할 종목이 없습니다."
        )

    started_at = datetime.now()

    print()
    print("=" * 88)
    print(
        "AI STOCK BOT V5.2 "
        "DAILY PREDICTION ENGINE"
    )
    print("=" * 88)

    print(
        f"Started at          : "
        f"{started_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        f"Symbols             : "
        f"{', '.join(cleaned_symbols)}"
    )

    print(
        f"Total symbols       : "
        f"{len(cleaned_symbols)}"
    )

    print("=" * 88)

    predictions: list[
        DailyPredictionResult
    ] = []

    total_symbols = len(
        cleaned_symbols
    )

    for index, symbol in enumerate(
        cleaned_symbols,
        start=1,
    ):
        print()
        print("#" * 88)

        print(
            f"[{index}/{total_symbols}] "
            f"{symbol}"
        )

        print("#" * 88)

        try:
            result = predict_symbol_daily(
                symbol=symbol,
                period=period,
                interval=interval,
            )

            predictions.append(
                result
            )

        except KeyboardInterrupt:
            print()
            print(
                "사용자가 예측 프로그램을 중단했습니다."
            )

            raise

        except Exception as error:
            failed_result = (
                create_failed_prediction(
                    symbol=symbol,
                    error=error,
                )
            )

            predictions.append(
                failed_result
            )

            print()
            print(
                f"{symbol} prediction failed: "
                f"{type(error).__name__} - {error}"
            )

            if not continue_on_error:
                raise

    successful_predictions = [
        result
        for result in predictions
        if result.success
    ]

    failed_predictions = [
        result
        for result in predictions
        if not result.success
    ]

    bullish_count = sum(
        1
        for result in successful_predictions
        if result.prediction == "BULLISH"
    )

    neutral_count = sum(
        1
        for result in successful_predictions
        if result.prediction == "NEUTRAL"
    )

    bearish_count = sum(
        1
        for result in successful_predictions
        if result.prediction == "BEARISH"
    )

    watch_buy_count = sum(
        1
        for result in successful_predictions
        if result.action_signal == "WATCH_BUY"
    )

    hold_count = sum(
        1
        for result in successful_predictions
        if result.action_signal == "HOLD"
    )

    avoid_count = sum(
        1
        for result in successful_predictions
        if result.action_signal == "AVOID"
    )

    ranked_predictions = sorted(
        successful_predictions,
        key=lambda item: (
            item.up_probability,
            item.confidence,
        ),
        reverse=True,
    )

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at - started_at
    ).total_seconds()

    report: dict[str, Any] = {
        "version": "V5.2",

        "started_at": (
            started_at.isoformat()
        ),

        "finished_at": (
            finished_at.isoformat()
        ),

        "elapsed_seconds": round(
            elapsed_seconds,
            2,
        ),

        "settings": {
            "symbols": cleaned_symbols,
            "period": period,
            "interval": interval,
            "continue_on_error": (
                continue_on_error
            ),
        },

        "summary": {
            "total_symbols": (
                len(cleaned_symbols)
            ),

            "successful_count": (
                len(successful_predictions)
            ),

            "failed_count": (
                len(failed_predictions)
            ),

            "bullish_count": (
                bullish_count
            ),

            "neutral_count": (
                neutral_count
            ),

            "bearish_count": (
                bearish_count
            ),

            "watch_buy_count": (
                watch_buy_count
            ),

            "hold_count": (
                hold_count
            ),

            "avoid_count": (
                avoid_count
            ),

            "top_symbol": (
                ranked_predictions[0].symbol
                if ranked_predictions
                else None
            ),

            "top_up_probability": (
                ranked_predictions[0]
                .up_probability
                if ranked_predictions
                else None
            ),
        },

        "predictions": [
            result.to_dict()
            for result in predictions
        ],

        "ranked_predictions": [
            result.to_dict()
            for result in ranked_predictions
        ],
    }

    json_path = None
    csv_path = None
    latest_json_path = None
    latest_csv_path = None

    if save_reports:
        ensure_output_directories()

        timestamp = (
            finished_at.strftime(
                "%Y%m%d_%H%M%S"
            )
        )

        json_path = (
            PREDICTION_DIRECTORY
            / (
                f"daily_prediction_"
                f"{timestamp}.json"
            )
        )

        csv_path = (
            PREDICTION_DIRECTORY
            / (
                f"daily_prediction_"
                f"{timestamp}.csv"
            )
        )

        latest_json_path = (
            OUTPUT_DIRECTORY
            / "daily_prediction_latest.json"
        )

        latest_csv_path = (
            OUTPUT_DIRECTORY
            / "daily_prediction_latest.csv"
        )

        report["files"] = {
            "json_report": str(
                json_path
            ),

            "csv_report": str(
                csv_path
            ),

            "latest_json_report": str(
                latest_json_path
            ),

            "latest_csv_report": str(
                latest_csv_path
            ),
        }

        save_json_report(
            report=report,
            dated_path=json_path,
            latest_path=latest_json_path,
        )

        save_csv_report(
            predictions=predictions,
            dated_path=csv_path,
            latest_path=latest_csv_path,
        )

    else:
        report["files"] = {
            "json_report": None,
            "csv_report": None,
            "latest_json_report": None,
            "latest_csv_report": None,
        }

    print_daily_prediction_summary(
        report
    )

    return report


def print_daily_prediction_summary(
    report: dict[str, Any],
) -> None:
    """
    전체 예측 요약을 터미널에 출력합니다.
    """

    summary = report.get(
        "summary",
        {},
    )

    ranked_predictions = report.get(
        "ranked_predictions",
        [],
    )

    print()
    print("=" * 118)
    print(
        "AI STOCK BOT V5.2 "
        "DAILY PREDICTION SUMMARY"
    )
    print("=" * 118)

    print(
        f"Successful          : "
        f"{summary.get('successful_count', 0)}"
    )

    print(
        f"Failed              : "
        f"{summary.get('failed_count', 0)}"
    )

    print(
        f"Bullish             : "
        f"{summary.get('bullish_count', 0)}"
    )

    print(
        f"Neutral             : "
        f"{summary.get('neutral_count', 0)}"
    )

    print(
        f"Bearish             : "
        f"{summary.get('bearish_count', 0)}"
    )

    print(
        f"Watch buy           : "
        f"{summary.get('watch_buy_count', 0)}"
    )

    print(
        f"Hold                : "
        f"{summary.get('hold_count', 0)}"
    )

    print(
        f"Avoid               : "
        f"{summary.get('avoid_count', 0)}"
    )

    print(
        f"Top probability     : "
        f"{summary.get('top_symbol') or 'N/A'} "
        f"{safe_float(summary.get('top_up_probability')):.2f}%"
    )

    print()
    print(
        f"{'Rank':<6}"
        f"{'Symbol':<10}"
        f"{'Prediction':<14}"
        f"{'Up Prob.':>11}"
        f"{'Down Prob.':>13}"
        f"{'Confidence':>13}"
        f"{'Level':>10}"
        f"{'Signal':>14}"
        f"{'Model':>22}"
    )

    print("-" * 118)

    for index, item in enumerate(
        ranked_predictions,
        start=1,
    ):
        print(
            f"{index:<6}"
            f"{str(item.get('symbol', '')):<10}"
            f"{str(item.get('prediction', '')):<14}"
            f"{safe_float(item.get('up_probability')):>10.2f}%"
            f"{safe_float(item.get('down_probability')):>12.2f}%"
            f"{safe_float(item.get('confidence')):>12.2f}%"
            f"{str(item.get('confidence_level', '')):>10}"
            f"{str(item.get('action_signal', '')):>14}"
            f"{str(item.get('model_name') or 'N/A'):>22}"
        )

    print("-" * 118)

    files = report.get(
        "files",
        {},
    )

    print()
    print(
        f"JSON report         : "
        f"{files.get('json_report') or 'Not saved'}"
    )

    print(
        f"CSV report          : "
        f"{files.get('csv_report') or 'Not saved'}"
    )

    print(
        f"Latest JSON         : "
        f"{files.get('latest_json_report') or 'Not saved'}"
    )

    print(
        f"Latest CSV          : "
        f"{files.get('latest_csv_report') or 'Not saved'}"
    )

    print("=" * 118)

    print()
    print(
        "주의: 이 결과는 저장된 실험적 머신러닝 모델의 "
        "참고 예측이며 투자 조언이나 수익 보장이 아닙니다."
    )