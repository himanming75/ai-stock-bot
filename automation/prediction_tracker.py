import csv
import json
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

PREDICTION_HISTORY_JSON_PATH = (
    OUTPUT_DIRECTORY
    / "prediction_history.json"
)

PREDICTION_HISTORY_CSV_PATH = (
    OUTPUT_DIRECTORY
    / "prediction_history.csv"
)

ACCURACY_REPORT_PATH = (
    OUTPUT_DIRECTORY
    / "prediction_accuracy_report.json"
)


def ensure_output_directory() -> None:
    """
    output 폴더가 없으면 생성합니다.
    """

    OUTPUT_DIRECTORY.mkdir(
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


def normalize_prediction(
    prediction: Any,
) -> str:
    """
    예측 문자열을 표준 형식으로 정리합니다.
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


def normalize_date_text(
    value: Any,
) -> str | None:
    """
    날짜 값을 YYYY-MM-DD 형식으로 정리합니다.
    """

    if value is None:
        return None

    try:
        timestamp = pd.Timestamp(
            value
        )

        return timestamp.strftime(
            "%Y-%m-%d"
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def load_json_file(
    path: Path,
    default: Any,
) -> Any:
    """
    JSON 파일을 안전하게 읽습니다.
    """

    if not path.exists():
        return default

    try:
        with path.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            return json.load(
                file
            )

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return default


def save_json_file(
    path: Path,
    data: Any,
) -> None:
    """
    데이터를 JSON 파일로 저장합니다.
    """

    ensure_output_directory()

    with path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def load_latest_prediction_report() -> dict[str, Any]:
    """
    V5.2에서 생성한 최신 예측 보고서를 읽습니다.
    """

    report = load_json_file(
        path=LATEST_PREDICTION_PATH,
        default={},
    )

    if not isinstance(
        report,
        dict,
    ):
        raise ValueError(
            "최신 예측 보고서의 형식이 올바르지 않습니다."
        )

    predictions = report.get(
        "predictions"
    )

    if not isinstance(
        predictions,
        list,
    ):
        raise ValueError(
            "daily_prediction_latest.json에서 "
            "predictions 목록을 찾지 못했습니다."
        )

    return report


def load_prediction_history() -> list[dict[str, Any]]:
    """
    기존 예측 이력을 읽습니다.
    """

    history = load_json_file(
        path=PREDICTION_HISTORY_JSON_PATH,
        default=[],
    )

    if not isinstance(
        history,
        list,
    ):
        return []

    return history


def build_prediction_id(
    prediction: dict[str, Any],
) -> str:
    """
    중복 저장 방지를 위한 고유 ID를 생성합니다.
    """

    symbol = normalize_symbol(
        prediction.get(
            "symbol",
            "UNKNOWN",
        )
    )

    market_data_date = (
        normalize_date_text(
            prediction.get(
                "market_data_date"
            )
        )
        or "UNKNOWN_DATE"
    )

    horizon = safe_int(
        prediction.get(
            "prediction_horizon"
        ),
        default=5,
    )

    model_name = str(
        prediction.get(
            "model_name"
        )
        or "UNKNOWN_MODEL"
    ).upper()

    return (
        f"{symbol}_"
        f"{market_data_date}_"
        f"H{horizon}_"
        f"{model_name}"
    )


def create_history_record(
    prediction: dict[str, Any],
) -> dict[str, Any]:
    """
    일일 예측 결과를 이력용 레코드로 변환합니다.
    """

    prediction_id = build_prediction_id(
        prediction
    )

    symbol = normalize_symbol(
        prediction.get(
            "symbol",
            "UNKNOWN",
        )
    )

    prediction_direction = (
        normalize_prediction(
            prediction.get(
                "prediction"
            )
        )
    )

    reference_close = safe_float(
        prediction.get(
            "latest_close"
        ),
        default=0.0,
    )

    return {
        "prediction_id": prediction_id,

        "symbol": symbol,

        "recorded_at": (
            datetime.now().isoformat()
        ),

        "generated_at": prediction.get(
            "generated_at"
        ),

        "market_data_date": (
            normalize_date_text(
                prediction.get(
                    "market_data_date"
                )
            )
        ),

        "prediction_horizon": safe_int(
            prediction.get(
                "prediction_horizon"
            ),
            default=5,
        ),

        "model_name": prediction.get(
            "model_name"
        ),

        "model_created_at": prediction.get(
            "model_created_at"
        ),

        "model_status": prediction.get(
            "model_status"
        ),

        "prediction": (
            prediction_direction
        ),

        "up_probability": safe_float(
            prediction.get(
                "up_probability"
            )
        ),

        "down_probability": safe_float(
            prediction.get(
                "down_probability"
            )
        ),

        "confidence": safe_float(
            prediction.get(
                "confidence"
            )
        ),

        "confidence_level": prediction.get(
            "confidence_level"
        ),

        "action_signal": prediction.get(
            "action_signal"
        ),

        "reference_close": (
            reference_close
        ),

        "evaluation_status": "PENDING",

        "target_market_date": None,

        "target_close": None,

        "actual_return_percent": None,

        "actual_direction": None,

        "is_correct": None,

        "result_label": "PENDING",

        "evaluated_at": None,

        "evaluation_message": (
            "예측 기간이 지나면 실제 가격과 비교합니다."
        ),
    }


def append_latest_predictions() -> dict[str, int]:
    """
    최신 성공 예측을 prediction_history.json에 추가합니다.

    동일한 prediction_id는 다시 추가하지 않습니다.
    """

    latest_report = (
        load_latest_prediction_report()
    )

    predictions = latest_report.get(
        "predictions",
        [],
    )

    history = load_prediction_history()

    existing_ids = {
        str(
            item.get(
                "prediction_id"
            )
        )
        for item in history
        if item.get(
            "prediction_id"
        )
    }

    added_count = 0
    skipped_count = 0
    failed_prediction_count = 0

    for prediction in predictions:
        if not isinstance(
            prediction,
            dict,
        ):
            continue

        if not prediction.get(
            "success",
            False,
        ):
            failed_prediction_count += 1
            continue

        record = create_history_record(
            prediction
        )

        prediction_id = record[
            "prediction_id"
        ]

        if prediction_id in existing_ids:
            skipped_count += 1
            continue

        history.append(
            record
        )

        existing_ids.add(
            prediction_id
        )

        added_count += 1

    save_json_file(
        path=PREDICTION_HISTORY_JSON_PATH,
        data=history,
    )

    return {
        "added_count": added_count,
        "skipped_count": skipped_count,
        "failed_prediction_count": (
            failed_prediction_count
        ),
        "history_count": len(
            history
        ),
    }


def prepare_market_history(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    주가 데이터의 날짜 인덱스를 정리합니다.
    """

    if data is None or data.empty:
        return pd.DataFrame()

    prepared = data.copy()

    prepared.index = pd.to_datetime(
        prepared.index
    )

    if prepared.index.tz is not None:
        prepared.index = (
            prepared.index.tz_localize(
                None
            )
        )

    prepared = prepared.sort_index()

    prepared = prepared[
        ~prepared.index.duplicated(
            keep="last"
        )
    ]

    return prepared


def find_target_market_row(
    data: pd.DataFrame,
    prediction_date: str,
    horizon_days: int,
) -> tuple[pd.Timestamp, pd.Series] | None:
    """
    예측일 이후 horizon_days번째 거래일을 찾습니다.

    예측일 다음 거래일을 1일째로 계산합니다.
    """

    prepared = prepare_market_history(
        data
    )

    if prepared.empty:
        return None

    start_date = pd.Timestamp(
        prediction_date
    )

    future_data = prepared[
        prepared.index > start_date
    ]

    if len(
        future_data
    ) < horizon_days:
        return None

    target_position = (
        horizon_days - 1
    )

    target_date = (
        future_data.index[
            target_position
        ]
    )

    target_row = future_data.iloc[
        target_position
    ]

    return target_date, target_row


def determine_actual_direction(
    return_percent: float,
    neutral_threshold_percent: float,
) -> str:
    """
    실제 수익률을 방향으로 변환합니다.
    """

    if (
        return_percent
        > neutral_threshold_percent
    ):
        return "BULLISH"

    if (
        return_percent
        < -neutral_threshold_percent
    ):
        return "BEARISH"

    return "NEUTRAL"


def determine_result(
    prediction: str,
    actual_direction: str,
) -> tuple[bool, str]:
    """
    예측과 실제 방향을 비교합니다.
    """

    normalized_prediction = (
        normalize_prediction(
            prediction
        )
    )

    if (
        normalized_prediction
        == actual_direction
    ):
        if actual_direction == "NEUTRAL":
            return True, "NEUTRAL_MATCH"

        return True, "CORRECT"

    return False, "WRONG"


def evaluate_history_record(
    record: dict[str, Any],
    data: pd.DataFrame,
    neutral_threshold_percent: float,
) -> bool:
    """
    한 개의 PENDING 예측을 평가합니다.

    평가가 완료되면 True,
    아직 미래 데이터가 부족하면 False를 반환합니다.
    """

    if (
        record.get(
            "evaluation_status"
        )
        == "COMPLETED"
    ):
        return False

    prediction_date = (
        normalize_date_text(
            record.get(
                "market_data_date"
            )
        )
    )

    if prediction_date is None:
        record[
            "evaluation_status"
        ] = "ERROR"

        record[
            "result_label"
        ] = "ERROR"

        record[
            "evaluation_message"
        ] = (
            "예측 기준 날짜가 없어 평가하지 못했습니다."
        )

        record[
            "evaluated_at"
        ] = datetime.now().isoformat()

        return True

    horizon_days = max(
        1,
        safe_int(
            record.get(
                "prediction_horizon"
            ),
            default=5,
        ),
    )

    target_result = (
        find_target_market_row(
            data=data,
            prediction_date=(
                prediction_date
            ),
            horizon_days=(
                horizon_days
            ),
        )
    )

    if target_result is None:
        return False

    (
        target_date,
        target_row,
    ) = target_result

    if "Close" not in target_row:
        record[
            "evaluation_status"
        ] = "ERROR"

        record[
            "result_label"
        ] = "ERROR"

        record[
            "evaluation_message"
        ] = (
            "시장 데이터에서 Close 값을 찾지 못했습니다."
        )

        record[
            "evaluated_at"
        ] = datetime.now().isoformat()

        return True

    reference_close = safe_float(
        record.get(
            "reference_close"
        )
    )

    target_close = safe_float(
        target_row["Close"]
    )

    if reference_close <= 0:
        record[
            "evaluation_status"
        ] = "ERROR"

        record[
            "result_label"
        ] = "ERROR"

        record[
            "evaluation_message"
        ] = (
            "예측 당시 기준 가격이 올바르지 않습니다."
        )

        record[
            "evaluated_at"
        ] = datetime.now().isoformat()

        return True

    return_percent = (
        (
            target_close
            - reference_close
        )
        / reference_close
    ) * 100.0

    actual_direction = (
        determine_actual_direction(
            return_percent=(
                return_percent
            ),
            neutral_threshold_percent=(
                neutral_threshold_percent
            ),
        )
    )

    (
        is_correct,
        result_label,
    ) = determine_result(
        prediction=str(
            record.get(
                "prediction",
                "NEUTRAL",
            )
        ),
        actual_direction=(
            actual_direction
        ),
    )

    record[
        "evaluation_status"
    ] = "COMPLETED"

    record[
        "target_market_date"
    ] = target_date.strftime(
        "%Y-%m-%d"
    )

    record[
        "target_close"
    ] = round(
        target_close,
        4,
    )

    record[
        "actual_return_percent"
    ] = round(
        return_percent,
        4,
    )

    record[
        "actual_direction"
    ] = actual_direction

    record[
        "is_correct"
    ] = is_correct

    record[
        "result_label"
    ] = result_label

    record[
        "evaluated_at"
    ] = datetime.now().isoformat()

    record[
        "evaluation_message"
    ] = (
        f"{horizon_days}거래일 후 실제 방향은 "
        f"{actual_direction}이며 "
        f"수익률은 {return_percent:+.2f}%입니다."
    )

    return True


def evaluate_pending_predictions(
    neutral_threshold_percent: float = 1.0,
    market_period: str = "10y",
    market_interval: str = "1d",
) -> dict[str, Any]:
    """
    평가 가능한 PENDING 예측을 실제 가격과 비교합니다.
    """

    history = load_prediction_history()

    pending_records = [
        item
        for item in history
        if item.get(
            "evaluation_status"
        )
        == "PENDING"
    ]

    symbols = sorted(
        {
            normalize_symbol(
                item.get(
                    "symbol",
                    ""
                )
            )
            for item in pending_records
            if item.get(
                "symbol"
            )
        }
    )

    evaluated_count = 0
    still_pending_count = 0
    error_count = 0

    market_cache: dict[
        str,
        pd.DataFrame
    ] = {}

    for symbol in symbols:
        try:
            market_data = get_history(
                symbol=symbol,
                period=market_period,
                interval=market_interval,
            )

            market_cache[
                symbol
            ] = prepare_market_history(
                market_data
            )

        except Exception as error:
            print(
                f"{symbol} 시장 데이터 다운로드 실패: "
                f"{type(error).__name__} - {error}"
            )

            market_cache[
                symbol
            ] = pd.DataFrame()

    for record in history:
        if (
            record.get(
                "evaluation_status"
            )
            != "PENDING"
        ):
            continue

        symbol = normalize_symbol(
            record.get(
                "symbol",
                ""
            )
        )

        data = market_cache.get(
            symbol,
            pd.DataFrame(),
        )

        if data.empty:
            still_pending_count += 1
            continue

        changed = evaluate_history_record(
            record=record,
            data=data,
            neutral_threshold_percent=(
                neutral_threshold_percent
            ),
        )

        if not changed:
            still_pending_count += 1
            continue

        if (
            record.get(
                "evaluation_status"
            )
            == "COMPLETED"
        ):
            evaluated_count += 1

        else:
            error_count += 1

    save_json_file(
        path=PREDICTION_HISTORY_JSON_PATH,
        data=history,
    )

    return {
        "evaluated_count": (
            evaluated_count
        ),

        "still_pending_count": (
            still_pending_count
        ),

        "error_count": (
            error_count
        ),

        "history_count": len(
            history
        ),
    }


def create_accuracy_report(
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    누적 예측 정확도 보고서를 생성합니다.
    """

    completed = [
        item
        for item in history
        if item.get(
            "evaluation_status"
        )
        == "COMPLETED"
    ]

    pending = [
        item
        for item in history
        if item.get(
            "evaluation_status"
        )
        == "PENDING"
    ]

    errors = [
        item
        for item in history
        if item.get(
            "evaluation_status"
        )
        == "ERROR"
    ]

    correct_count = sum(
        1
        for item in completed
        if item.get(
            "is_correct"
        )
        is True
    )

    wrong_count = sum(
        1
        for item in completed
        if item.get(
            "is_correct"
        )
        is False
    )

    accuracy_percent = 0.0

    if completed:
        accuracy_percent = (
            correct_count
            / len(completed)
        ) * 100.0

    direction_summary: dict[
        str,
        dict[str, Any]
    ] = {}

    for direction in (
        "BULLISH",
        "NEUTRAL",
        "BEARISH",
    ):
        direction_records = [
            item
            for item in completed
            if item.get(
                "prediction"
            )
            == direction
        ]

        direction_correct = sum(
            1
            for item in direction_records
            if item.get(
                "is_correct"
            )
            is True
        )

        direction_accuracy = 0.0

        if direction_records:
            direction_accuracy = (
                direction_correct
                / len(
                    direction_records
                )
            ) * 100.0

        direction_summary[
            direction
        ] = {
            "total": len(
                direction_records
            ),

            "correct": (
                direction_correct
            ),

            "accuracy_percent": round(
                direction_accuracy,
                2,
            ),
        }

    symbol_summary: dict[
        str,
        dict[str, Any]
    ] = {}

    symbols = sorted(
        {
            str(
                item.get(
                    "symbol"
                )
            )
            for item in history
            if item.get(
                "symbol"
            )
        }
    )

    for symbol in symbols:
        symbol_completed = [
            item
            for item in completed
            if item.get(
                "symbol"
            )
            == symbol
        ]

        symbol_correct = sum(
            1
            for item in symbol_completed
            if item.get(
                "is_correct"
            )
            is True
        )

        symbol_accuracy = 0.0

        if symbol_completed:
            symbol_accuracy = (
                symbol_correct
                / len(
                    symbol_completed
                )
            ) * 100.0

        symbol_summary[
            symbol
        ] = {
            "completed": len(
                symbol_completed
            ),

            "correct": (
                symbol_correct
            ),

            "wrong": (
                len(symbol_completed)
                - symbol_correct
            ),

            "accuracy_percent": round(
                symbol_accuracy,
                2,
            ),
        }

    return {
        "version": "V5.3",

        "generated_at": (
            datetime.now().isoformat()
        ),

        "summary": {
            "total_records": len(
                history
            ),

            "completed_count": len(
                completed
            ),

            "pending_count": len(
                pending
            ),

            "error_count": len(
                errors
            ),

            "correct_count": (
                correct_count
            ),

            "wrong_count": (
                wrong_count
            ),

            "accuracy_percent": round(
                accuracy_percent,
                2,
            ),
        },

        "direction_summary": (
            direction_summary
        ),

        "symbol_summary": (
            symbol_summary
        ),
    }


def save_history_csv(
    history: list[dict[str, Any]],
) -> None:
    """
    예측 이력을 CSV 파일로 저장합니다.
    """

    ensure_output_directory()

    fieldnames = [
        "prediction_id",
        "symbol",
        "recorded_at",
        "generated_at",
        "market_data_date",
        "prediction_horizon",
        "model_name",
        "model_created_at",
        "model_status",
        "prediction",
        "up_probability",
        "down_probability",
        "confidence",
        "confidence_level",
        "action_signal",
        "reference_close",
        "evaluation_status",
        "target_market_date",
        "target_close",
        "actual_return_percent",
        "actual_direction",
        "is_correct",
        "result_label",
        "evaluated_at",
        "evaluation_message",
    ]

    with PREDICTION_HISTORY_CSV_PATH.open(
        mode="w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for record in history:
            row = {
                field: record.get(
                    field
                )
                for field in fieldnames
            }

            writer.writerow(
                row
            )


def print_tracker_summary(
    append_result: dict[str, int],
    evaluation_result: dict[str, Any],
    accuracy_report: dict[str, Any],
) -> None:
    """
    Tracker 실행 결과를 터미널에 출력합니다.
    """

    summary = accuracy_report.get(
        "summary",
        {},
    )

    print()
    print("=" * 90)
    print(
        "AI STOCK BOT V5.3 "
        "PREDICTION HISTORY TRACKER"
    )
    print("=" * 90)

    print(
        f"New predictions added : "
        f"{append_result.get('added_count', 0)}"
    )

    print(
        f"Duplicates skipped    : "
        f"{append_result.get('skipped_count', 0)}"
    )

    print(
        f"Failed predictions    : "
        f"{append_result.get('failed_prediction_count', 0)}"
    )

    print(
        f"Evaluated now         : "
        f"{evaluation_result.get('evaluated_count', 0)}"
    )

    print(
        f"Still pending         : "
        f"{summary.get('pending_count', 0)}"
    )

    print(
        f"Completed total       : "
        f"{summary.get('completed_count', 0)}"
    )

    print(
        f"Correct total         : "
        f"{summary.get('correct_count', 0)}"
    )

    print(
        f"Wrong total           : "
        f"{summary.get('wrong_count', 0)}"
    )

    print(
        f"Overall accuracy      : "
        f"{safe_float(summary.get('accuracy_percent')):.2f}%"
    )

    print()
    print(
        f"History JSON          : "
        f"{PREDICTION_HISTORY_JSON_PATH}"
    )

    print(
        f"History CSV           : "
        f"{PREDICTION_HISTORY_CSV_PATH}"
    )

    print(
        f"Accuracy report       : "
        f"{ACCURACY_REPORT_PATH}"
    )

    print("=" * 90)


def run_prediction_tracker(
    neutral_threshold_percent: float = 1.0,
) -> dict[str, Any]:
    """
    V5.3 전체 실행 함수입니다.

    1. 최신 예측 추가
    2. 평가 가능한 과거 예측 확인
    3. 실제 결과와 비교
    4. 누적 정확도 저장
    5. CSV 저장
    """

    if neutral_threshold_percent < 0:
        raise ValueError(
            "neutral_threshold_percent는 "
            "0 이상이어야 합니다."
        )

    ensure_output_directory()

    append_result = (
        append_latest_predictions()
    )

    evaluation_result = (
        evaluate_pending_predictions(
            neutral_threshold_percent=(
                neutral_threshold_percent
            )
        )
    )

    history = load_prediction_history()

    accuracy_report = (
        create_accuracy_report(
            history
        )
    )

    accuracy_report[
        "neutral_threshold_percent"
    ] = neutral_threshold_percent

    save_json_file(
        path=ACCURACY_REPORT_PATH,
        data=accuracy_report,
    )

    save_history_csv(
        history
    )

    print_tracker_summary(
        append_result=append_result,
        evaluation_result=(
            evaluation_result
        ),
        accuracy_report=(
            accuracy_report
        ),
    )

    return {
        "append_result": (
            append_result
        ),

        "evaluation_result": (
            evaluation_result
        ),

        "accuracy_report": (
            accuracy_report
        ),

        "files": {
            "history_json": str(
                PREDICTION_HISTORY_JSON_PATH
            ),

            "history_csv": str(
                PREDICTION_HISTORY_CSV_PATH
            ),

            "accuracy_report": str(
                ACCURACY_REPORT_PATH
            ),
        },
    }