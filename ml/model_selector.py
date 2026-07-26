from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import ClassifierMixin
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.predictor import (
    FEATURE_COLUMNS,
    build_feature_frame,
    build_training_dataset,
    get_latest_feature_row,
)


@dataclass
class ModelEvaluation:
    """
    한 머신러닝 모델의 시계열 검증 결과입니다.
    """

    model_name: str

    accuracy: float
    balanced_accuracy: float
    precision: float
    recall: float

    validation_rows: int
    successful_splits: int

    upward_probability: float
    prediction: str

    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ModelSelectionResult:
    """
    여러 모델을 비교한 최종 결과입니다.
    """

    symbol: str
    prediction_date: str
    horizon_days: int

    selected_model: str
    selected_prediction: str
    selected_upward_probability: float
    selected_balanced_accuracy: float

    ensemble_upward_probability: float
    ensemble_prediction: str

    training_rows: int
    feature_count: int

    evaluations: list[ModelEvaluation]

    selection_status: str
    warning: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_random_forest() -> RandomForestClassifier:
    """
    Random Forest 모델입니다.
    """

    return RandomForestClassifier(
        n_estimators=400,
        max_depth=8,
        min_samples_split=14,
        min_samples_leaf=7,
        max_features="sqrt",
        class_weight="balanced_subsample",
        random_state=42,

        # Windows와 일부 최신 Python 환경에서
        # 반복되는 joblib 경고를 줄이기 위해
        # 우선 단일 프로세스로 실행합니다.
        n_jobs=1,
    )


def create_logistic_regression() -> Pipeline:
    """
    StandardScaler와 Logistic Regression을
    하나의 Pipeline으로 묶습니다.
    """

    return Pipeline(
        steps=[
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2000,
                    class_weight="balanced",
                    solver="liblinear",
                    random_state=42,
                ),
            ),
        ]
    )


def create_gradient_boosting() -> GradientBoostingClassifier:
    """
    Gradient Boosting 모델입니다.
    """

    return GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.03,
        max_depth=3,
        min_samples_split=14,
        min_samples_leaf=7,
        subsample=0.85,
        random_state=42,
    )


def create_candidate_models() -> dict[
    str,
    ClassifierMixin,
]:
    """
    비교할 모델 목록을 반환합니다.
    """

    return {
        "RANDOM_FOREST": (
            create_random_forest()
        ),
        "LOGISTIC_REGRESSION": (
            create_logistic_regression()
        ),
        "GRADIENT_BOOSTING": (
            create_gradient_boosting()
        ),
    }


def determine_prediction(
    upward_probability: float,
) -> str:
    """
    상승 확률을 방향 예측으로 변환합니다.
    """

    if upward_probability >= 65.0:
        return "BULLISH"

    if upward_probability <= 35.0:
        return "BEARISH"

    return "NEUTRAL"


def determine_model_status(
    balanced_accuracy: float,
) -> str:
    """
    균형 정확도를 모델 상태로 변환합니다.
    """

    if balanced_accuracy >= 60.0:
        return "USABLE"

    if balanced_accuracy >= 55.0:
        return "PROMISING"

    if balanced_accuracy >= 50.0:
        return "EXPERIMENTAL"

    return "WEAK"


def get_positive_probability(
    model: ClassifierMixin,
    features: pd.DataFrame,
) -> float:
    """
    클래스 1, 즉 상승 확률을 가져옵니다.
    """

    if not hasattr(
        model,
        "predict_proba",
    ):
        return 50.0

    probabilities = model.predict_proba(
        features
    )[0]

    classes = model.classes_

    class_probability_map = {
        int(class_name): float(probability)
        for class_name, probability
        in zip(
            classes,
            probabilities,
        )
    }

    return (
        class_probability_map.get(
            1,
            0.5,
        )
        * 100.0
    )


def evaluate_model(
    model_name: str,
    model: ClassifierMixin,
    dataset: pd.DataFrame,
    latest_features: pd.DataFrame,
    horizon_days: int,
    n_splits: int = 5,
) -> ModelEvaluation:
    """
    하나의 모델을 시계열 분할로 검증하고
    최신 상승 확률을 계산합니다.
    """

    features = dataset[
        FEATURE_COLUMNS
    ]

    target = dataset[
        "TARGET"
    ]

    splitter = TimeSeriesSplit(
        n_splits=n_splits,
        gap=horizon_days,
    )

    actual_values: list[int] = []
    predicted_values: list[int] = []

    successful_splits = 0
    validation_rows = 0

    for train_indices, test_indices in (
        splitter.split(features)
    ):
        train_features = features.iloc[
            train_indices
        ]

        train_target = target.iloc[
            train_indices
        ]

        test_features = features.iloc[
            test_indices
        ]

        test_target = target.iloc[
            test_indices
        ]

        if train_target.nunique() < 2:
            continue

        fold_model = clone_model(
            model_name
        )

        fold_model.fit(
            train_features,
            train_target,
        )

        predictions = fold_model.predict(
            test_features
        )

        actual_values.extend(
            test_target.astype(int).tolist()
        )

        predicted_values.extend(
            predictions.astype(int).tolist()
        )

        successful_splits += 1
        validation_rows += len(
            test_indices
        )

    if not actual_values:
        return ModelEvaluation(
            model_name=model_name,

            accuracy=0.0,
            balanced_accuracy=0.0,
            precision=0.0,
            recall=0.0,

            validation_rows=0,
            successful_splits=0,

            upward_probability=50.0,
            prediction="NEUTRAL",

            status="FAILED",
        )

    accuracy = accuracy_score(
        actual_values,
        predicted_values,
    )

    balanced_accuracy = (
        balanced_accuracy_score(
            actual_values,
            predicted_values,
        )
    )

    precision = precision_score(
        actual_values,
        predicted_values,
        zero_division=0,
    )

    recall = recall_score(
        actual_values,
        predicted_values,
        zero_division=0,
    )

    final_model = clone_model(
        model_name
    )

    final_model.fit(
        features,
        target,
    )

    upward_probability = (
        get_positive_probability(
            model=final_model,
            features=latest_features,
        )
    )

    balanced_accuracy_percent = round(
        float(
            balanced_accuracy
        )
        * 100.0,
        2,
    )

    return ModelEvaluation(
        model_name=model_name,

        accuracy=round(
            float(accuracy) * 100.0,
            2,
        ),

        balanced_accuracy=(
            balanced_accuracy_percent
        ),

        precision=round(
            float(precision) * 100.0,
            2,
        ),

        recall=round(
            float(recall) * 100.0,
            2,
        ),

        validation_rows=validation_rows,
        successful_splits=successful_splits,

        upward_probability=round(
            upward_probability,
            2,
        ),

        prediction=determine_prediction(
            upward_probability
        ),

        status=determine_model_status(
            balanced_accuracy_percent
        ),
    )


def clone_model(
    model_name: str,
) -> ClassifierMixin:
    """
    모델 이름에 맞는 새 모델을 생성합니다.

    각 시계열 분할마다 완전히 새로운
    모델을 사용하기 위한 함수입니다.
    """

    models = create_candidate_models()

    if model_name not in models:
        raise ValueError(
            "지원하지 않는 모델입니다: "
            f"{model_name}"
        )

    return models[
        model_name
    ]


def calculate_ensemble_probability(
    evaluations: list[ModelEvaluation],
) -> float:
    """
    모델별 균형 정확도를 가중치로 사용해
    앙상블 상승 확률을 계산합니다.

    검증력이 50% 미만인 모델은
    앙상블에 거의 영향을 주지 않습니다.
    """

    weighted_probability = 0.0
    total_weight = 0.0

    for evaluation in evaluations:
        if evaluation.status == "FAILED":
            continue

        weight = max(
            0.01,
            evaluation.balanced_accuracy
            - 49.0,
        )

        weighted_probability += (
            evaluation.upward_probability
            * weight
        )

        total_weight += weight

    if total_weight <= 0:
        return 50.0

    return round(
        weighted_probability
        / total_weight,
        2,
    )


def select_best_model(
    evaluations: list[ModelEvaluation],
) -> ModelEvaluation:
    """
    균형 정확도를 가장 중요하게 보고,
    이후 정확도와 정밀도로 최적 모델을 선택합니다.
    """

    successful_evaluations = [
        evaluation
        for evaluation in evaluations
        if evaluation.status != "FAILED"
    ]

    if not successful_evaluations:
        raise ValueError(
            "성공적으로 평가된 모델이 없습니다."
        )

    return max(
        successful_evaluations,
        key=lambda evaluation: (
            evaluation.balanced_accuracy,
            evaluation.accuracy,
            evaluation.precision,
        ),
    )


def determine_selection_status(
    selected_model: ModelEvaluation,
) -> tuple[str, str]:
    """
    최종 모델 선택 결과의 안전 상태를 정합니다.
    """

    if (
        selected_model.balanced_accuracy
        < 50.0
    ):
        return (
            "RESEARCH_ONLY",
            "선택된 최상위 모델도 균형 정확도가 "
            "50% 미만입니다.",
        )

    if (
        selected_model.balanced_accuracy
        < 55.0
    ):
        return (
            "EXPERIMENTAL",
            "최상위 모델의 검증 성능이 낮아 "
            "참고용으로만 사용해야 합니다.",
        )

    if (
        selected_model.balanced_accuracy
        < 60.0
    ):
        return (
            "PROMISING",
            "일부 예측력이 보이지만 더 긴 기간과 "
            "다른 종목에서 검증해야 합니다.",
        )

    return (
        "USABLE",
        "과거 검증은 양호하지만 미래 수익을 "
        "보장하지 않습니다.",
    )


def format_prediction_date(
    index_value: Any,
) -> str:
    """
    데이터 인덱스를 날짜 문자열로 바꿉니다.
    """

    if hasattr(
        index_value,
        "strftime",
    ):
        return index_value.strftime(
            "%Y-%m-%d"
        )

    return str(index_value)


def compare_models(
    symbol: str,
    data: pd.DataFrame,
    horizon_days: int = 5,
    minimum_return: float = 0.0,
) -> ModelSelectionResult:
    """
    세 모델을 비교하여 가장 검증력이 높은
    모델과 앙상블 상승 확률을 반환합니다.
    """

    normalized_symbol = (
        str(symbol)
        .upper()
        .strip()
    )

    if not normalized_symbol:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    feature_frame = build_feature_frame(
        data
    )

    dataset = build_training_dataset(
        feature_frame=feature_frame,
        horizon_days=horizon_days,
        minimum_return=minimum_return,
    )

    if len(dataset) < 300:
        raise ValueError(
            "모델 비교에 필요한 데이터가 "
            "부족합니다. "
            f"현재 행 수: {len(dataset)}"
        )

    if dataset["TARGET"].nunique() < 2:
        raise ValueError(
            "TARGET이 한 종류뿐이라 "
            "분류 모델을 비교할 수 없습니다."
        )

    latest_row = get_latest_feature_row(
        feature_frame
    )

    latest_features = latest_row[
        FEATURE_COLUMNS
    ]

    evaluations: list[
        ModelEvaluation
    ] = []

    candidate_models = (
        create_candidate_models()
    )

    for model_name, model in (
        candidate_models.items()
    ):
        evaluation = evaluate_model(
            model_name=model_name,
            model=model,
            dataset=dataset,
            latest_features=latest_features,
            horizon_days=horizon_days,
            n_splits=5,
        )

        evaluations.append(
            evaluation
        )

    selected_model = select_best_model(
        evaluations
    )

    ensemble_probability = (
        calculate_ensemble_probability(
            evaluations
        )
    )

    selection_status, warning = (
        determine_selection_status(
            selected_model
        )
    )

    prediction_date = (
        format_prediction_date(
            latest_row.index[-1]
        )
    )

    return ModelSelectionResult(
        symbol=normalized_symbol,
        prediction_date=prediction_date,
        horizon_days=horizon_days,

        selected_model=(
            selected_model.model_name
        ),

        selected_prediction=(
            selected_model.prediction
        ),

        selected_upward_probability=(
            selected_model.upward_probability
        ),

        selected_balanced_accuracy=(
            selected_model.balanced_accuracy
        ),

        ensemble_upward_probability=(
            ensemble_probability
        ),

        ensemble_prediction=(
            determine_prediction(
                ensemble_probability
            )
        ),

        training_rows=len(dataset),
        feature_count=len(
            FEATURE_COLUMNS
        ),

        evaluations=evaluations,

        selection_status=(
            selection_status
        ),

        warning=warning,
    )


def print_model_comparison(
    result: ModelSelectionResult,
) -> None:
    """
    모델 비교 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 94)
    print(
        f"{result.symbol} MACHINE LEARNING MODEL COMPARISON V4.4"
    )
    print("=" * 94)

    print(
        f"Prediction date     : "
        f"{result.prediction_date}"
    )

    print(
        f"Prediction horizon  : "
        f"{result.horizon_days} trading days"
    )

    print(
        f"Training rows       : "
        f"{result.training_rows}"
    )

    print(
        f"Feature count       : "
        f"{result.feature_count}"
    )

    print()
    print(
        f"{'Model':<24}"
        f"{'Accuracy':>12}"
        f"{'Balanced':>12}"
        f"{'Precision':>12}"
        f"{'Recall':>10}"
        f"{'Up Prob':>11}"
        f"{'Prediction':>13}"
        f"{'Status':>14}"
    )

    print("-" * 108)

    for evaluation in result.evaluations:
        print(
            f"{evaluation.model_name:<24}"
            f"{evaluation.accuracy:>11.2f}%"
            f"{evaluation.balanced_accuracy:>11.2f}%"
            f"{evaluation.precision:>11.2f}%"
            f"{evaluation.recall:>9.2f}%"
            f"{evaluation.upward_probability:>10.2f}%"
            f"{evaluation.prediction:>13}"
            f"{evaluation.status:>14}"
        )

    print("-" * 108)

    print(
        f"Selected model      : "
        f"{result.selected_model}"
    )

    print(
        f"Selected prediction : "
        f"{result.selected_prediction}"
    )

    print(
        f"Selected up prob.   : "
        f"{result.selected_upward_probability:.2f}%"
    )

    print(
        f"Selected bal. acc.  : "
        f"{result.selected_balanced_accuracy:.2f}%"
    )

    print()
    print(
        f"Ensemble prediction : "
        f"{result.ensemble_prediction}"
    )

    print(
        f"Ensemble up prob.   : "
        f"{result.ensemble_upward_probability:.2f}%"
    )

    print(
        f"Selection status    : "
        f"{result.selection_status}"
    )

    print()
    print(
        f"Warning: "
        f"{result.warning}"
    )

    print(
        "Model comparison is based on historical "
        "validation and is not investment advice."
    )