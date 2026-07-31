import math
import random
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import TimeSeriesSplit

MODEL_RANDOM_SEED = 42
MODEL_N_JOBS = 1


FEATURE_COLUMNS = [
    # 가격과 이동평균
    "PRICE_VS_MA5",
    "PRICE_VS_MA20",
    "MA5_VS_MA20",
    "MA5_SLOPE_3D",
    "MA20_SLOPE_5D",

    # 수익률과 모멘텀
    "DAILY_RETURN",
    "RETURN_2D",
    "RETURN_3D",
    "RETURN_5D",
    "RETURN_10D",
    "RETURN_20D",
    "MOMENTUM_5D",
    "MOMENTUM_10D",

    # RSI와 MACD
    "RSI_NORMALIZED",
    "RSI_CHANGE_3D",
    "MACD_NORMALIZED",
    "MACD_HIST_NORMALIZED",
    "MACD_HIST_CHANGE_3D",

    # 볼린저 밴드
    "BB_POSITION",
    "BB_WIDTH",
    "DISTANCE_FROM_BB_UPPER",
    "DISTANCE_FROM_BB_LOWER",

    # 변동성
    "VOLATILITY_5D",
    "VOLATILITY_10D",
    "VOLATILITY_20D",
    "ATR_PERCENT",

    # 일중 가격 구조
    "DAILY_RANGE_PERCENT",
    "CLOSE_POSITION_IN_RANGE",
    "GAP_PERCENT",

    # 거래량
    "VOLUME_CHANGE",
    "VOLUME_VS_5D",
    "VOLUME_VS_20D",

    # 고점·저점 대비 위치
    "PRICE_VS_20D_HIGH",
    "PRICE_VS_20D_LOW",
    "PRICE_VS_60D_HIGH",
    "PRICE_VS_60D_LOW",
]


@dataclass
class MLPrediction:
    """
    한 종목의 머신러닝 예측 결과입니다.
    """

    symbol: str
    prediction_date: str
    prediction_horizon_days: int

    prediction: str
    upward_probability: float
    downward_probability: float

    latest_close: float

    validation_accuracy: float
    validation_balanced_accuracy: float
    validation_precision: float
    validation_recall: float

    positive_class_percent: float

    training_rows: int
    validation_rows: int
    feature_count: int

    feature_importance: dict[str, float]

    model_status: str
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


def validate_market_data(
    data: pd.DataFrame,
) -> None:
    """
    필요한 시장 데이터 컬럼을 확인합니다.
    """

    required_columns = {
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "MA5",
        "MA20",
        "RSI",
        "MACD",
        "MACD_HIST",
        "BB_UPPER",
        "BB_LOWER",
    }

    missing_columns = (
        required_columns
        - set(data.columns)
    )

    if missing_columns:
        raise ValueError(
            "머신러닝에 필요한 컬럼이 없습니다: "
            + ", ".join(sorted(missing_columns))
        )

    if data.empty:
        raise ValueError(
            "머신러닝에 사용할 데이터가 없습니다."
        )


def safe_divide(
    numerator,
    denominator,
):
    """
    0으로 나누는 오류를 방지합니다.
    """

    if isinstance(denominator, pd.Series):
        safe_denominator = denominator.replace(
            0,
            np.nan,
        )
    else:
        safe_denominator = (
            np.nan
            if denominator == 0
            else denominator
        )

    return numerator / safe_denominator


def calculate_true_range(
    data: pd.DataFrame,
) -> pd.Series:
    """
    ATR 계산에 필요한 True Range를 계산합니다.
    """

    previous_close = data["Close"].shift(1)

    high_low = (
        data["High"]
        - data["Low"]
    ).abs()

    high_previous = (
        data["High"]
        - previous_close
    ).abs()

    low_previous = (
        data["Low"]
        - previous_close
    ).abs()

    return pd.concat(
        [
            high_low,
            high_previous,
            low_previous,
        ],
        axis=1,
    ).max(axis=1)


def build_feature_frame(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    원본 시장 데이터에서 머신러닝 특징을 계산합니다.

    이 함수는 Target을 만들지 않으므로
    최신 날짜까지 유지합니다.
    """

    validate_market_data(data)

    frame = data.copy()

    close = frame["Close"]
    open_price = frame["Open"]
    high = frame["High"]
    low = frame["Low"]
    volume = frame["Volume"]

    daily_return = close.pct_change()

    # --------------------------------------------------------
    # 가격과 이동평균
    # --------------------------------------------------------

    frame["PRICE_VS_MA5"] = (
        safe_divide(
            close,
            frame["MA5"],
        )
        - 1
    )

    frame["PRICE_VS_MA20"] = (
        safe_divide(
            close,
            frame["MA20"],
        )
        - 1
    )

    frame["MA5_VS_MA20"] = (
        safe_divide(
            frame["MA5"],
            frame["MA20"],
        )
        - 1
    )

    frame["MA5_SLOPE_3D"] = (
        frame["MA5"].pct_change(3)
    )

    frame["MA20_SLOPE_5D"] = (
        frame["MA20"].pct_change(5)
    )

    # --------------------------------------------------------
    # 수익률과 모멘텀
    # --------------------------------------------------------

    frame["DAILY_RETURN"] = daily_return
    frame["RETURN_2D"] = close.pct_change(2)
    frame["RETURN_3D"] = close.pct_change(3)
    frame["RETURN_5D"] = close.pct_change(5)
    frame["RETURN_10D"] = close.pct_change(10)
    frame["RETURN_20D"] = close.pct_change(20)

    frame["MOMENTUM_5D"] = (
        safe_divide(
            close,
            close.shift(5),
        )
        - 1
    )

    frame["MOMENTUM_10D"] = (
        safe_divide(
            close,
            close.shift(10),
        )
        - 1
    )

    # --------------------------------------------------------
    # RSI와 MACD
    # --------------------------------------------------------

    frame["RSI_NORMALIZED"] = (
        frame["RSI"] / 100.0
    )

    frame["RSI_CHANGE_3D"] = (
        frame["RSI"].diff(3) / 100.0
    )

    frame["MACD_NORMALIZED"] = safe_divide(
        frame["MACD"],
        close,
    )

    frame["MACD_HIST_NORMALIZED"] = safe_divide(
        frame["MACD_HIST"],
        close,
    )

    frame["MACD_HIST_CHANGE_3D"] = safe_divide(
        frame["MACD_HIST"].diff(3),
        close,
    )

    # --------------------------------------------------------
    # 볼린저 밴드
    # --------------------------------------------------------

    bollinger_width = (
        frame["BB_UPPER"]
        - frame["BB_LOWER"]
    )

    frame["BB_POSITION"] = safe_divide(
        close - frame["BB_LOWER"],
        bollinger_width,
    )

    frame["BB_WIDTH"] = safe_divide(
        bollinger_width,
        close,
    )

    frame["DISTANCE_FROM_BB_UPPER"] = (
        safe_divide(
            frame["BB_UPPER"],
            close,
        )
        - 1
    )

    frame["DISTANCE_FROM_BB_LOWER"] = (
        safe_divide(
            close,
            frame["BB_LOWER"],
        )
        - 1
    )

    # --------------------------------------------------------
    # 변동성
    # --------------------------------------------------------

    frame["VOLATILITY_5D"] = (
        daily_return
        .rolling(5)
        .std()
    )

    frame["VOLATILITY_10D"] = (
        daily_return
        .rolling(10)
        .std()
    )

    frame["VOLATILITY_20D"] = (
        daily_return
        .rolling(20)
        .std()
    )

    true_range = calculate_true_range(
        frame
    )

    atr_14 = true_range.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    frame["ATR_PERCENT"] = safe_divide(
        atr_14,
        close,
    )

    # --------------------------------------------------------
    # 일중 가격 구조
    # --------------------------------------------------------

    daily_range = high - low

    frame["DAILY_RANGE_PERCENT"] = safe_divide(
        daily_range,
        close,
    )

    frame["CLOSE_POSITION_IN_RANGE"] = safe_divide(
        close - low,
        daily_range,
    )

    frame["GAP_PERCENT"] = (
        safe_divide(
            open_price,
            close.shift(1),
        )
        - 1
    )

    # --------------------------------------------------------
    # 거래량
    # --------------------------------------------------------

    frame["VOLUME_CHANGE"] = (
        volume.pct_change()
    )

    volume_ma5 = volume.rolling(5).mean()
    volume_ma20 = volume.rolling(20).mean()

    frame["VOLUME_VS_5D"] = (
        safe_divide(
            volume,
            volume_ma5,
        )
        - 1
    )

    frame["VOLUME_VS_20D"] = (
        safe_divide(
            volume,
            volume_ma20,
        )
        - 1
    )

    # --------------------------------------------------------
    # 최근 고점·저점 대비 현재 위치
    # --------------------------------------------------------

    high_20 = high.rolling(20).max()
    low_20 = low.rolling(20).min()

    high_60 = high.rolling(60).max()
    low_60 = low.rolling(60).min()

    frame["PRICE_VS_20D_HIGH"] = (
        safe_divide(
            close,
            high_20,
        )
        - 1
    )

    frame["PRICE_VS_20D_LOW"] = (
        safe_divide(
            close,
            low_20,
        )
        - 1
    )

    frame["PRICE_VS_60D_HIGH"] = (
        safe_divide(
            close,
            high_60,
        )
        - 1
    )

    frame["PRICE_VS_60D_LOW"] = (
        safe_divide(
            close,
            low_60,
        )
        - 1
    )

    frame = frame.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    return frame


def build_training_dataset(
    feature_frame: pd.DataFrame,
    horizon_days: int = 5,
    minimum_return: float = 0.0,
) -> pd.DataFrame:
    """
    특징 데이터에 미래 수익률과 Target을 추가합니다.

    미래 가격을 알고 있는 과거 행만
    학습 데이터로 사용합니다.
    """

    if horizon_days <= 0:
        raise ValueError(
            "horizon_days는 1 이상이어야 합니다."
        )

    dataset = feature_frame.copy()

    dataset["FUTURE_CLOSE"] = (
        dataset["Close"]
        .shift(-horizon_days)
    )

    dataset["FUTURE_RETURN"] = (
        safe_divide(
            dataset["FUTURE_CLOSE"],
            dataset["Close"],
        )
        - 1
    )

    dataset["TARGET"] = (
        dataset["FUTURE_RETURN"]
        > minimum_return
    ).astype(int)

    # 미래 결과가 확인되지 않은 마지막 horizon 행은 제거
    dataset = dataset.dropna(
        subset=(
            FEATURE_COLUMNS
            + [
                "FUTURE_CLOSE",
                "FUTURE_RETURN",
            ]
        )
    )

    return dataset


def get_latest_feature_row(
    feature_frame: pd.DataFrame,
) -> pd.DataFrame:
    """
    실제 예측에 사용할 가장 최신 특징 행을 반환합니다.
    """

    usable_features = feature_frame.dropna(
        subset=FEATURE_COLUMNS
    )

    if usable_features.empty:
        raise ValueError(
            "최신 머신러닝 특징 데이터가 없습니다."
        )

    return usable_features.iloc[[-1]]


def create_model() -> RandomForestClassifier:
    """
    Random Forest 모델을 생성합니다.
    """

    return RandomForestClassifier(
        n_estimators=500,
        max_depth=8,
        min_samples_split=14,
        min_samples_leaf=7,
        max_features="sqrt",
        class_weight="balanced_subsample",
        random_state=MODEL_RANDOM_SEED,
        n_jobs=MODEL_N_JOBS,
    )


def calculate_time_series_metrics(
    dataset: pd.DataFrame,
    horizon_days: int,
    n_splits: int = 5,
) -> tuple[
    float,
    float,
    float,
    float,
    int,
]:
    """
    시계열 순서를 지키며 검증합니다.

    gap=horizon_days를 사용해
    학습 대상 미래 구간과 검증 구간이
    겹치는 문제를 줄입니다.
    """

    if len(dataset) < 300:
        raise ValueError(
            "시계열 검증 데이터가 부족합니다. "
            f"현재 행 수: {len(dataset)}"
        )

    split_count = min(
        max(2, n_splits),
        5,
    )

    time_series_split = TimeSeriesSplit(
        n_splits=split_count,
        gap=horizon_days,
    )

    actual_values: list[int] = []
    predicted_values: list[int] = []

    validation_rows = 0

    features = dataset[
        FEATURE_COLUMNS
    ]

    target = dataset["TARGET"]

    for train_indices, test_indices in (
        time_series_split.split(features)
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

        model = create_model()

        model.fit(
            train_features,
            train_target,
        )

        predictions = model.predict(
            test_features
        )

        actual_values.extend(
            test_target.astype(int).tolist()
        )

        predicted_values.extend(
            predictions.astype(int).tolist()
        )

        validation_rows += len(
            test_indices
        )

    if not actual_values:
        return (
            0.0,
            0.0,
            0.0,
            0.0,
            0,
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

    return (
        round(float(accuracy) * 100, 2),
        round(
            float(balanced_accuracy) * 100,
            2,
        ),
        round(float(precision) * 100, 2),
        round(float(recall) * 100, 2),
        validation_rows,
    )


def get_upward_probability(
    model: RandomForestClassifier,
    latest_features: pd.DataFrame,
) -> float:
    """
    상승 클래스 1의 확률을 반환합니다.
    """

    probabilities = model.predict_proba(
        latest_features
    )[0]

    class_probability_map = {
        int(class_name): float(probability)
        for class_name, probability
        in zip(
            model.classes_,
            probabilities,
        )
    }

    return class_probability_map.get(
        1,
        0.0,
    )


def determine_prediction(
    upward_probability: float,
) -> str:
    """
    상승 확률을 예측 상태로 변환합니다.
    """

    if upward_probability >= 0.65:
        return "BULLISH"

    if upward_probability <= 0.35:
        return "BEARISH"

    return "NEUTRAL"


def determine_model_status(
    balanced_accuracy: float,
    training_rows: int,
) -> tuple[str, str]:
    """
    모델의 검증 성능을 평가합니다.
    """

    if training_rows < 500:
        return (
            "LOW_DATA",
            "학습 데이터가 적어 예측 신뢰가 낮을 수 있습니다.",
        )

    if balanced_accuracy < 50:
        return (
            "WEAK",
            "균형 정확도가 50% 미만이므로 실전 판단에 사용하면 안 됩니다.",
        )

    if balanced_accuracy < 55:
        return (
            "EXPERIMENTAL",
            "검증 성능이 낮아 연구·참고 목적으로만 사용해야 합니다.",
        )

    if balanced_accuracy < 60:
        return (
            "PROMISING",
            "일부 예측력이 관찰되지만 추가 검증이 필요합니다.",
        )

    return (
        "USABLE",
        "과거 검증 성능은 양호하지만 미래 성과를 보장하지 않습니다.",
    )


def format_prediction_date(
    index_value,
) -> str:
    """
    데이터 인덱스를 날짜 문자열로 변환합니다.
    """

    if hasattr(index_value, "strftime"):
        return index_value.strftime(
            "%Y-%m-%d"
        )

    return str(index_value)


def predict_stock_direction(
    symbol: str,
    data: pd.DataFrame,
    horizon_days: int = 5,
    minimum_return: float = 0.0,
) -> MLPrediction:
    """
    최신 데이터를 이용하여 향후 상승 확률을 계산합니다.
    """

    random.seed(MODEL_RANDOM_SEED)
    np.random.seed(MODEL_RANDOM_SEED)

    symbol = (
        str(symbol)
        .upper()
        .strip()
    )

    if not symbol:
        raise ValueError(
            "symbol이 비어 있습니다."
        )

    # 최신 날짜까지 특징 계산
    feature_frame = build_feature_frame(
        data
    )

    # 미래 결과가 확인된 과거 행만 학습에 사용
    training_dataset = build_training_dataset(
        feature_frame=feature_frame,
        horizon_days=horizon_days,
        minimum_return=minimum_return,
    )

    if len(training_dataset) < 300:
        raise ValueError(
            "머신러닝 학습 데이터가 부족합니다. "
            f"현재 행 수: {len(training_dataset)}"
        )

    training_target = (
        training_dataset["TARGET"]
    )

    if training_target.nunique() < 2:
        raise ValueError(
            "학습 Target이 한 종류뿐이라 "
            "분류 모델을 만들 수 없습니다."
        )

    (
        validation_accuracy,
        validation_balanced_accuracy,
        validation_precision,
        validation_recall,
        validation_rows,
    ) = calculate_time_series_metrics(
        dataset=training_dataset,
        horizon_days=horizon_days,
        n_splits=5,
    )

    training_features = training_dataset[
        FEATURE_COLUMNS
    ]

    model = create_model()

    model.fit(
        training_features,
        training_target,
    )

    # 미래 결과가 없는 실제 최신 행을 예측에 사용
    latest_row = get_latest_feature_row(
        feature_frame
    )

    latest_features = latest_row[
        FEATURE_COLUMNS
    ]

    upward_probability = (
        get_upward_probability(
            model=model,
            latest_features=latest_features,
        )
    )

    downward_probability = (
        1.0 - upward_probability
    )

    prediction = determine_prediction(
        upward_probability
    )

    feature_importance = {
        feature_name: round(
            float(importance) * 100,
            2,
        )
        for feature_name, importance
        in zip(
            FEATURE_COLUMNS,
            model.feature_importances_,
        )
    }

    feature_importance = dict(
        sorted(
            feature_importance.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )

    (
        model_status,
        warning,
    ) = determine_model_status(
        balanced_accuracy=(
            validation_balanced_accuracy
        ),
        training_rows=len(
            training_dataset
        ),
    )

    latest_close = float(
        latest_row["Close"].iloc[0]
    )

    if not math.isfinite(latest_close):
        raise ValueError(
            "최신 종가가 정상적인 숫자가 아닙니다."
        )

    positive_class_percent = (
        training_target.mean() * 100
    )

    prediction_date = format_prediction_date(
        latest_row.index[-1]
    )

    return MLPrediction(
        symbol=symbol,
        prediction_date=prediction_date,

        prediction_horizon_days=(
            horizon_days
        ),

        prediction=prediction,

        upward_probability=round(
            upward_probability * 100,
            2,
        ),

        downward_probability=round(
            downward_probability * 100,
            2,
        ),

        latest_close=round(
            latest_close,
            2,
        ),

        validation_accuracy=(
            validation_accuracy
        ),

        validation_balanced_accuracy=(
            validation_balanced_accuracy
        ),

        validation_precision=(
            validation_precision
        ),

        validation_recall=(
            validation_recall
        ),

        positive_class_percent=round(
            float(positive_class_percent),
            2,
        ),

        training_rows=len(
            training_dataset
        ),

        validation_rows=(
            validation_rows
        ),

        feature_count=len(
            FEATURE_COLUMNS
        ),

        feature_importance=(
            feature_importance
        ),

        model_status=model_status,
        warning=warning,
    )


def print_ml_prediction(
    prediction: MLPrediction,
) -> None:
    """
    머신러닝 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 70)
    print(
        f"{prediction.symbol} MACHINE LEARNING PREDICTION V4.1"
    )
    print("=" * 70)

    print(
        f"Prediction date     : "
        f"{prediction.prediction_date}"
    )

    print(
        f"Prediction horizon  : "
        f"{prediction.prediction_horizon_days} trading days"
    )

    print(
        f"Latest close        : "
        f"${prediction.latest_close:,.2f}"
    )

    print(
        f"Prediction          : "
        f"{prediction.prediction}"
    )

    print(
        f"Up probability      : "
        f"{prediction.upward_probability:.2f}%"
    )

    print(
        f"Down probability    : "
        f"{prediction.downward_probability:.2f}%"
    )

    print("-" * 70)

    print(
        f"Validation accuracy : "
        f"{prediction.validation_accuracy:.2f}%"
    )

    print(
        f"Balanced accuracy   : "
        f"{prediction.validation_balanced_accuracy:.2f}%"
    )

    print(
        f"Validation precision: "
        f"{prediction.validation_precision:.2f}%"
    )

    print(
        f"Validation recall   : "
        f"{prediction.validation_recall:.2f}%"
    )

    print(
        f"Positive class rate : "
        f"{prediction.positive_class_percent:.2f}%"
    )

    print(
        f"Training rows       : "
        f"{prediction.training_rows}"
    )

    print(
        f"Validation rows     : "
        f"{prediction.validation_rows}"
    )

    print(
        f"Feature count       : "
        f"{prediction.feature_count}"
    )

    print(
        f"Model status        : "
        f"{prediction.model_status}"
    )

    print()
    print("Most important features:")

    for feature_name, importance in list(
        prediction.feature_importance.items()
    )[:10]:
        print(
            f"- {feature_name}: "
            f"{importance:.2f}%"
        )

    print()
    print(
        f"Warning: "
        f"{prediction.warning}"
    )

    print(
        "This is an experimental historical model, "
        "not a guaranteed forecast or investment advice."
    )