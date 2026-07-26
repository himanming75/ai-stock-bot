import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from ml.model_history import append_model_history
from ml.model_selector import (
    ModelSelectionResult,
    clone_model,
    compare_models,
    determine_prediction,
)
from ml.predictor import (
    FEATURE_COLUMNS,
    build_feature_frame,
    build_training_dataset,
    get_latest_feature_row,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIRECTORY = PROJECT_ROOT / "models"


@dataclass
class SavedModelInfo:
    """
    저장된 최적 머신러닝 모델의 정보입니다.
    """

    symbol: str
    model_name: str

    created_at: str
    prediction_date: str
    horizon_days: int

    training_rows: int
    feature_count: int

    balanced_accuracy: float
    validation_accuracy: float
    validation_precision: float
    validation_recall: float

    latest_upward_probability: float
    latest_prediction: str

    ensemble_upward_probability: float
    ensemble_prediction: str

    selection_status: str
    warning: str

    model_path: str
    metadata_path: str
    history_path: str

    feature_columns: list[str]

    def to_dict(self) -> dict[str, Any]:
        """
        dataclass를 일반 dictionary로 변환합니다.
        """

        return asdict(self)


def normalize_symbol(
    symbol: str,
) -> str:
    """
    종목 코드를 대문자로 정리합니다.
    """

    normalized_symbol = (
        str(symbol)
        .upper()
        .strip()
    )

    if not normalized_symbol:
        raise ValueError(
            "종목 코드가 비어 있습니다."
        )

    return normalized_symbol


def ensure_model_directory() -> Path:
    """
    모델 저장 폴더를 생성합니다.
    """

    MODEL_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    return MODEL_DIRECTORY


def get_model_paths(
    symbol: str,
) -> tuple[Path, Path]:
    """
    종목별 모델 파일과 JSON 파일 경로를 만듭니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    model_directory = ensure_model_directory()

    model_path = (
        model_directory
        / f"{normalized_symbol}_best_model.joblib"
    )

    metadata_path = (
        model_directory
        / f"{normalized_symbol}_best_model.json"
    )

    return (
        model_path,
        metadata_path,
    )


def find_selected_evaluation(
    selection_result: ModelSelectionResult,
):
    """
    선택된 모델에 해당하는 검증 결과를 찾습니다.
    """

    for evaluation in (
        selection_result.evaluations
    ):
        if (
            evaluation.model_name
            == selection_result.selected_model
        ):
            return evaluation

    raise ValueError(
        "선택된 모델의 검증 결과를 "
        "찾을 수 없습니다."
    )


def get_positive_probability(
    model: Any,
    features: pd.DataFrame,
) -> float:
    """
    학습된 모델에서 상승 클래스 1의 확률을 가져옵니다.
    """

    if not hasattr(
        model,
        "predict_proba",
    ):
        return 50.0

    probabilities = model.predict_proba(
        features
    )[0]

    classes = getattr(
        model,
        "classes_",
        [],
    )

    class_probability_map = {
        int(class_name): float(probability)
        for class_name, probability
        in zip(
            classes,
            probabilities,
        )
    }

    return round(
        class_probability_map.get(
            1,
            0.5,
        )
        * 100.0,
        2,
    )


def save_metadata(
    metadata: SavedModelInfo,
    metadata_path: Path,
) -> None:
    """
    모델 정보를 JSON 파일로 저장합니다.
    """

    with metadata_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata.to_dict(),
            file,
            ensure_ascii=False,
            indent=2,
        )


def format_prediction_date(
    value: Any,
) -> str:
    """
    날짜 또는 인덱스 값을 문자열로 변환합니다.
    """

    if hasattr(
        value,
        "strftime",
    ):
        return value.strftime(
            "%Y-%m-%d"
        )

    return str(value)


def train_and_save_best_model(
    symbol: str,
    data: pd.DataFrame,
    horizon_days: int = 5,
    minimum_return: float = 0.0,
) -> SavedModelInfo:
    """
    여러 모델을 비교하고 최적 모델을 다시 학습한 뒤
    모델 파일, 메타데이터 및 모델 성능 이력을 저장합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if data is None or data.empty:
        raise ValueError(
            "모델 학습에 사용할 시장 데이터가 없습니다."
        )

    print()
    print("=" * 80)
    print(
        f"TRAINING BEST MODEL FOR "
        f"{normalized_symbol}"
    )
    print("=" * 80)

    print(
        "Comparing candidate models..."
    )

    selection_result = compare_models(
        symbol=normalized_symbol,
        data=data,
        horizon_days=horizon_days,
        minimum_return=minimum_return,
    )

    selected_evaluation = (
        find_selected_evaluation(
            selection_result
        )
    )

    print(
        f"Selected model      : "
        f"{selection_result.selected_model}"
    )

    print(
        f"Balanced accuracy   : "
        f"{selected_evaluation.balanced_accuracy:.2f}%"
    )

    # 특징 데이터 생성
    feature_frame = build_feature_frame(
        data
    )

    if feature_frame.empty:
        raise ValueError(
            "머신러닝 특징 데이터를 생성하지 못했습니다."
        )

    # 학습 데이터 생성
    training_dataset = build_training_dataset(
        feature_frame=feature_frame,
        horizon_days=horizon_days,
        minimum_return=minimum_return,
    )

    if training_dataset.empty:
        raise ValueError(
            "최종 모델 학습 데이터가 없습니다."
        )

    missing_columns = (
        set(FEATURE_COLUMNS)
        - set(training_dataset.columns)
    )

    if missing_columns:
        raise ValueError(
            "학습 데이터에 필요한 특징 열이 없습니다: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    if "TARGET" not in training_dataset.columns:
        raise ValueError(
            "학습 데이터에 TARGET 열이 없습니다."
        )

    training_features = training_dataset[
        FEATURE_COLUMNS
    ].copy()

    training_target = training_dataset[
        "TARGET"
    ].copy()

    if training_target.nunique() < 2:
        raise ValueError(
            "TARGET 값이 한 종류뿐이라 "
            "최종 모델을 학습할 수 없습니다."
        )

    print(
        "Training selected model on full dataset..."
    )

    selected_model = clone_model(
        selection_result.selected_model
    )

    selected_model.fit(
        training_features,
        training_target,
    )

    # 최신 날짜 특징으로 저장 직전 예측 확인
    latest_row = get_latest_feature_row(
        feature_frame
    )

    if latest_row.empty:
        raise ValueError(
            "최신 예측에 사용할 특징 데이터가 없습니다."
        )

    latest_missing_columns = (
        set(FEATURE_COLUMNS)
        - set(latest_row.columns)
    )

    if latest_missing_columns:
        raise ValueError(
            "최신 특징 데이터에 필요한 열이 없습니다: "
            + ", ".join(
                sorted(latest_missing_columns)
            )
        )

    latest_features = latest_row[
        FEATURE_COLUMNS
    ].copy()

    latest_upward_probability = (
        get_positive_probability(
            model=selected_model,
            features=latest_features,
        )
    )

    latest_prediction = determine_prediction(
        latest_upward_probability
    )

    prediction_date = format_prediction_date(
        latest_row.index[-1]
    )

    (
        model_path,
        metadata_path,
    ) = get_model_paths(
        normalized_symbol
    )

    created_at = datetime.now().isoformat()

    # 모델과 모델 실행에 필요한 정보를 함께 저장합니다.
    model_package = {
        "symbol": normalized_symbol,

        "model_name": (
            selection_result.selected_model
        ),

        "model": selected_model,

        "feature_columns": list(
            FEATURE_COLUMNS
        ),

        "horizon_days": int(
            horizon_days
        ),

        "minimum_return": float(
            minimum_return
        ),

        "created_at": created_at,

        "prediction_date": prediction_date,

        "balanced_accuracy": float(
            selected_evaluation.balanced_accuracy
        ),

        "selection_status": (
            selection_result.selection_status
        ),
    }

    joblib.dump(
        model_package,
        model_path,
    )

    # 모델 성능 이력 누적 저장
    history_path = append_model_history(
        symbol=normalized_symbol,

        model_name=(
            selection_result.selected_model
        ),

        balanced_accuracy=(
            selected_evaluation.balanced_accuracy
        ),

        validation_accuracy=(
            selected_evaluation.accuracy
        ),

        validation_precision=(
            selected_evaluation.precision
        ),

        validation_recall=(
            selected_evaluation.recall
        ),

        prediction=latest_prediction,

        upward_probability=(
            latest_upward_probability
        ),

        ensemble_prediction=(
            selection_result.ensemble_prediction
        ),

        ensemble_upward_probability=(
            selection_result
            .ensemble_upward_probability
        ),

        selection_status=(
            selection_result.selection_status
        ),

        training_rows=len(
            training_dataset
        ),

        feature_count=len(
            FEATURE_COLUMNS
        ),

        prediction_date=prediction_date,

        model_path=str(
            model_path
        ),
    )

    metadata = SavedModelInfo(
        symbol=normalized_symbol,

        model_name=(
            selection_result.selected_model
        ),

        created_at=created_at,

        prediction_date=prediction_date,

        horizon_days=int(
            horizon_days
        ),

        training_rows=len(
            training_dataset
        ),

        feature_count=len(
            FEATURE_COLUMNS
        ),

        balanced_accuracy=float(
            selected_evaluation.balanced_accuracy
        ),

        validation_accuracy=float(
            selected_evaluation.accuracy
        ),

        validation_precision=float(
            selected_evaluation.precision
        ),

        validation_recall=float(
            selected_evaluation.recall
        ),

        latest_upward_probability=float(
            latest_upward_probability
        ),

        latest_prediction=(
            latest_prediction
        ),

        ensemble_upward_probability=float(
            selection_result
            .ensemble_upward_probability
        ),

        ensemble_prediction=(
            selection_result
            .ensemble_prediction
        ),

        selection_status=(
            selection_result.selection_status
        ),

        warning=(
            selection_result.warning
        ),

        model_path=str(
            model_path
        ),

        metadata_path=str(
            metadata_path
        ),

        history_path=str(
            history_path
        ),

        feature_columns=list(
            FEATURE_COLUMNS
        ),
    )

    save_metadata(
        metadata=metadata,
        metadata_path=metadata_path,
    )

    print()
    print("MODEL SAVED")

    print(
        f"Model file          : "
        f"{model_path}"
    )

    print(
        f"Metadata file       : "
        f"{metadata_path}"
    )

    print(
        f"History file        : "
        f"{history_path}"
    )

    print(
        f"Latest prediction   : "
        f"{latest_prediction}"
    )

    print(
        f"Latest up prob.     : "
        f"{latest_upward_probability:.2f}%"
    )

    print(
        f"Model status        : "
        f"{selection_result.selection_status}"
    )

    print("=" * 80)

    return metadata


def load_saved_model(
    symbol: str,
) -> dict[str, Any]:
    """
    저장된 종목 모델을 불러옵니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    model_path, _ = get_model_paths(
        normalized_symbol
    )

    if not model_path.exists():
        raise FileNotFoundError(
            "저장된 모델이 없습니다: "
            f"{model_path}"
        )

    model_package = joblib.load(
        model_path
    )

    if not isinstance(
        model_package,
        dict,
    ):
        raise ValueError(
            "저장된 모델 파일 형식이 올바르지 않습니다."
        )

    required_keys = {
        "symbol",
        "model_name",
        "model",
        "feature_columns",
        "horizon_days",
        "created_at",
    }

    missing_keys = (
        required_keys
        - set(model_package.keys())
    )

    if missing_keys:
        raise ValueError(
            "저장된 모델 파일에 필요한 정보가 없습니다: "
            + ", ".join(
                sorted(missing_keys)
            )
        )

    stored_symbol = normalize_symbol(
        model_package["symbol"]
    )

    if stored_symbol != normalized_symbol:
        raise ValueError(
            "저장 모델의 종목 코드가 요청한 종목과 다릅니다. "
            f"요청: {normalized_symbol}, "
            f"저장: {stored_symbol}"
        )

    return model_package


def predict_with_saved_model(
    symbol: str,
    data: pd.DataFrame,
) -> dict[str, Any]:
    """
    저장된 모델을 다시 학습하지 않고
    최신 데이터에 바로 적용합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if data is None or data.empty:
        raise ValueError(
            "예측에 사용할 시장 데이터가 없습니다."
        )

    model_package = load_saved_model(
        normalized_symbol
    )

    model = model_package[
        "model"
    ]

    feature_columns = list(
        model_package[
            "feature_columns"
        ]
    )

    feature_frame = build_feature_frame(
        data
    )

    if feature_frame.empty:
        raise ValueError(
            "예측용 특징 데이터를 생성하지 못했습니다."
        )

    latest_row = get_latest_feature_row(
        feature_frame
    )

    if latest_row.empty:
        raise ValueError(
            "최신 예측용 데이터가 없습니다."
        )

    missing_columns = (
        set(feature_columns)
        - set(latest_row.columns)
    )

    if missing_columns:
        raise ValueError(
            "저장된 모델이 요구하는 특징 열이 없습니다: "
            + ", ".join(
                sorted(missing_columns)
            )
        )

    latest_features = latest_row[
        feature_columns
    ].copy()

    upward_probability = (
        get_positive_probability(
            model=model,
            features=latest_features,
        )
    )

    prediction = determine_prediction(
        upward_probability
    )

    prediction_date = format_prediction_date(
        latest_row.index[-1]
    )

    if "Close" not in latest_row.columns:
        raise ValueError(
            "최신 데이터에 Close 열이 없습니다."
        )

    latest_close = round(
        float(
            latest_row[
                "Close"
            ].iloc[0]
        ),
        2,
    )

    return {
        "symbol": normalized_symbol,

        "model_name": model_package[
            "model_name"
        ],

        "model_created_at": (
            model_package[
                "created_at"
            ]
        ),

        "prediction_date": (
            prediction_date
        ),

        "horizon_days": int(
            model_package[
                "horizon_days"
            ]
        ),

        "latest_close": (
            latest_close
        ),

        "prediction": (
            prediction
        ),

        "upward_probability": float(
            upward_probability
        ),

        "downward_probability": round(
            100.0
            - upward_probability,
            2,
        ),

        "balanced_accuracy": float(
            model_package.get(
                "balanced_accuracy",
                0.0,
            )
        ),

        "selection_status": str(
            model_package.get(
                "selection_status",
                "UNKNOWN",
            )
        ),
    }


def print_saved_prediction(
    prediction: dict[str, Any],
) -> None:
    """
    저장된 모델의 최신 예측 결과를 출력합니다.
    """

    print()
    print("=" * 70)

    print(
        f"{prediction['symbol']} "
        "SAVED MODEL PREDICTION"
    )

    print("=" * 70)

    print(
        f"Model               : "
        f"{prediction['model_name']}"
    )

    print(
        f"Model created       : "
        f"{prediction['model_created_at']}"
    )

    print(
        f"Prediction date     : "
        f"{prediction['prediction_date']}"
    )

    print(
        f"Prediction horizon  : "
        f"{prediction['horizon_days']} "
        "trading days"
    )

    print(
        f"Latest close        : "
        f"${prediction['latest_close']:,.2f}"
    )

    print(
        f"Prediction          : "
        f"{prediction['prediction']}"
    )

    print(
        f"Up probability      : "
        f"{prediction['upward_probability']:.2f}%"
    )

    print(
        f"Down probability    : "
        f"{prediction['downward_probability']:.2f}%"
    )

    print(
        f"Balanced accuracy   : "
        f"{prediction.get('balanced_accuracy', 0.0):.2f}%"
    )

    print(
        f"Model status        : "
        f"{prediction.get('selection_status', 'UNKNOWN')}"
    )

    print("=" * 70)

    print(
        "This saved model is an experimental "
        "historical model, not investment advice."
    )