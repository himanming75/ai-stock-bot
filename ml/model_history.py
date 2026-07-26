import json
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIRECTORY = PROJECT_ROOT / "models"


def normalize_symbol(symbol: str) -> str:
    """
    종목 코드를 대문자로 정리합니다.
    """

    normalized = str(symbol).upper().strip()

    if not normalized:
        raise ValueError(
            "종목 코드가 비어 있습니다."
        )

    return normalized


def ensure_model_directory() -> Path:
    """
    models 폴더를 생성합니다.
    """

    MODEL_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    return MODEL_DIRECTORY


def get_history_path(
    symbol: str,
) -> Path:
    """
    종목별 모델 이력 파일 경로를 반환합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    model_directory = ensure_model_directory()

    return (
        model_directory
        / f"{normalized_symbol}_model_history.json"
    )


def load_model_history(
    symbol: str,
) -> list[dict[str, Any]]:
    """
    저장된 모델 성능 이력을 불러옵니다.

    파일이 없으면 빈 목록을 반환합니다.
    """

    history_path = get_history_path(
        symbol
    )

    if not history_path.exists():
        return []

    try:
        with history_path.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            data = json.load(
                file
            )

    except json.JSONDecodeError:
        print(
            "Warning: 모델 이력 JSON 파일이 "
            "손상되어 새 이력으로 시작합니다."
        )

        return []

    if not isinstance(
        data,
        list,
    ):
        return []

    return data


def save_model_history(
    symbol: str,
    history: list[dict[str, Any]],
) -> Path:
    """
    모델 이력 전체를 JSON 파일로 저장합니다.
    """

    history_path = get_history_path(
        symbol
    )

    with history_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            history,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return history_path


def append_model_history(
    symbol: str,
    model_name: str,
    balanced_accuracy: float,
    validation_accuracy: float,
    validation_precision: float,
    validation_recall: float,
    prediction: str,
    upward_probability: float,
    ensemble_prediction: str,
    ensemble_upward_probability: float,
    selection_status: str,
    training_rows: int,
    feature_count: int,
    prediction_date: str,
    model_path: str,
) -> Path:
    """
    최신 학습 결과를 모델 이력에 추가합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    history = load_model_history(
        normalized_symbol
    )

    record = {
        "recorded_at": (
            datetime.now().isoformat()
        ),

        "symbol": normalized_symbol,

        "model_name": str(
            model_name
        ),

        "balanced_accuracy": round(
            float(
                balanced_accuracy
            ),
            2,
        ),

        "validation_accuracy": round(
            float(
                validation_accuracy
            ),
            2,
        ),

        "validation_precision": round(
            float(
                validation_precision
            ),
            2,
        ),

        "validation_recall": round(
            float(
                validation_recall
            ),
            2,
        ),

        "prediction": str(
            prediction
        ),

        "upward_probability": round(
            float(
                upward_probability
            ),
            2,
        ),

        "ensemble_prediction": str(
            ensemble_prediction
        ),

        "ensemble_upward_probability": round(
            float(
                ensemble_upward_probability
            ),
            2,
        ),

        "selection_status": str(
            selection_status
        ),

        "training_rows": int(
            training_rows
        ),

        "feature_count": int(
            feature_count
        ),

        "prediction_date": str(
            prediction_date
        ),

        "model_path": str(
            model_path
        ),
    }

    history.append(
        record
    )

    return save_model_history(
        symbol=normalized_symbol,
        history=history,
    )


def get_latest_history_record(
    symbol: str,
) -> dict[str, Any] | None:
    """
    가장 최근 모델 이력 한 건을 반환합니다.
    """

    history = load_model_history(
        symbol
    )

    if not history:
        return None

    return history[-1]


def get_best_history_record(
    symbol: str,
) -> dict[str, Any] | None:
    """
    저장된 이력 중 균형 정확도가 가장 높은
    기록을 반환합니다.
    """

    history = load_model_history(
        symbol
    )

    if not history:
        return None

    return max(
        history,
        key=lambda item: float(
            item.get(
                "balanced_accuracy",
                0.0,
            )
        ),
    )


def print_model_history_summary(
    symbol: str,
) -> None:
    """
    종목의 모델 이력 요약을 터미널에 출력합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    history = load_model_history(
        normalized_symbol
    )

    print()
    print("=" * 92)
    print(
        f"{normalized_symbol} MODEL HISTORY V4.6"
    )
    print("=" * 92)

    if not history:
        print(
            "저장된 모델 이력이 없습니다."
        )

        return

    print(
        f"History count       : "
        f"{len(history)}"
    )

    print()

    print(
        f"{'No.':<6}"
        f"{'Recorded At':<27}"
        f"{'Model':<24}"
        f"{'Balanced':>11}"
        f"{'Up Prob':>11}"
        f"{'Prediction':>13}"
        f"{'Status':>15}"
    )

    print("-" * 108)

    for index, record in enumerate(
        history,
        start=1,
    ):
        print(
            f"{index:<6}"
            f"{str(record.get('recorded_at', '')):<27}"
            f"{str(record.get('model_name', '')):<24}"
            f"{float(record.get('balanced_accuracy', 0.0)):>10.2f}%"
            f"{float(record.get('upward_probability', 0.0)):>10.2f}%"
            f"{str(record.get('prediction', '')):>13}"
            f"{str(record.get('selection_status', '')):>15}"
        )

    print("-" * 108)

    latest_record = get_latest_history_record(
        normalized_symbol
    )

    best_record = get_best_history_record(
        normalized_symbol
    )

    if latest_record is not None:
        print(
            f"Latest model        : "
            f"{latest_record.get('model_name')}"
        )

        print(
            f"Latest balanced acc.: "
            f"{float(latest_record.get('balanced_accuracy', 0.0)):.2f}%"
        )

    if best_record is not None:
        print(
            f"Best historical model: "
            f"{best_record.get('model_name')}"
        )

        print(
            f"Best balanced acc.  : "
            f"{float(best_record.get('balanced_accuracy', 0.0)):.2f}%"
        )

    print("=" * 92)