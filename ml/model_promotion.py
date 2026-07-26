import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ml.model_history import (
    get_best_history_record,
    get_latest_history_record,
)
from ml.model_selector import ModelSelectionResult


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIRECTORY = PROJECT_ROOT / "models"


@dataclass
class ModelPromotionDecision:
    """
    신규 모델을 기존 저장 모델과 비교한 결과입니다.
    """

    symbol: str
    decision: str
    should_promote: bool

    candidate_model: str
    candidate_balanced_accuracy: float

    current_model: str | None
    current_balanced_accuracy: float | None

    best_historical_model: str | None
    best_historical_balanced_accuracy: float | None

    improvement_over_current: float | None
    improvement_over_best: float | None

    minimum_required_accuracy: float
    minimum_improvement: float

    reason: str

    def to_dict(self) -> dict[str, Any]:
        """
        dataclass를 dictionary로 변환합니다.
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


def get_metadata_path(
    symbol: str,
) -> Path:
    """
    저장된 최적 모델 메타데이터 경로를 반환합니다.
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    return (
        MODEL_DIRECTORY
        / f"{normalized_symbol}_best_model.json"
    )


def load_saved_model_metadata(
    symbol: str,
) -> dict[str, Any] | None:
    """
    현재 저장된 모델의 메타데이터를 읽습니다.

    파일이 없거나 읽을 수 없으면 None을 반환합니다.
    """

    metadata_path = get_metadata_path(
        symbol
    )

    if not metadata_path.exists():
        return None

    try:
        with metadata_path.open(
            mode="r",
            encoding="utf-8",
        ) as file:
            metadata = json.load(
                file
            )

    except (
        json.JSONDecodeError,
        OSError,
    ):
        return None

    if not isinstance(
        metadata,
        dict,
    ):
        return None

    return metadata


def find_selected_evaluation(
    selection_result: ModelSelectionResult,
):
    """
    선택된 후보 모델의 평가 결과를 찾습니다.
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
        "선택된 후보 모델의 평가 결과를 "
        "찾을 수 없습니다."
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


def evaluate_model_promotion(
    symbol: str,
    selection_result: ModelSelectionResult,
    minimum_required_accuracy: float = 50.0,
    minimum_improvement: float = 0.50,
) -> ModelPromotionDecision:
    """
    후보 모델을 기존 저장 모델과 비교하여
    실제 모델 파일을 교체할지 결정합니다.

    기본 기준:

    1. 후보 Balanced Accuracy가 50% 이상
    2. 기존 모델보다 최소 0.50%p 이상 개선
    3. 역사상 최고 기록보다 낮으면 보수적으로 유지
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    if minimum_required_accuracy < 0:
        raise ValueError(
            "minimum_required_accuracy는 "
            "0 이상이어야 합니다."
        )

    if minimum_improvement < 0:
        raise ValueError(
            "minimum_improvement는 "
            "0 이상이어야 합니다."
        )

    selected_evaluation = (
        find_selected_evaluation(
            selection_result
        )
    )

    candidate_model = (
        selected_evaluation.model_name
    )

    candidate_accuracy = safe_float(
        selected_evaluation.balanced_accuracy
    )

    current_metadata = (
        load_saved_model_metadata(
            normalized_symbol
        )
    )

    latest_history = (
        get_latest_history_record(
            normalized_symbol
        )
    )

    best_history = (
        get_best_history_record(
            normalized_symbol
        )
    )

    current_model: str | None = None
    current_accuracy: float | None = None

    if current_metadata is not None:
        current_model = str(
            current_metadata.get(
                "model_name",
                "UNKNOWN",
            )
        )

        current_accuracy = safe_float(
            current_metadata.get(
                "balanced_accuracy"
            )
        )

    elif latest_history is not None:
        current_model = str(
            latest_history.get(
                "model_name",
                "UNKNOWN",
            )
        )

        current_accuracy = safe_float(
            latest_history.get(
                "balanced_accuracy"
            )
        )

    best_model: str | None = None
    best_accuracy: float | None = None

    if best_history is not None:
        best_model = str(
            best_history.get(
                "model_name",
                "UNKNOWN",
            )
        )

        best_accuracy = safe_float(
            best_history.get(
                "balanced_accuracy"
            )
        )

    improvement_over_current: (
        float | None
    ) = None

    if current_accuracy is not None:
        improvement_over_current = round(
            candidate_accuracy
            - current_accuracy,
            2,
        )

    improvement_over_best: (
        float | None
    ) = None

    if best_accuracy is not None:
        improvement_over_best = round(
            candidate_accuracy
            - best_accuracy,
            2,
        )

    # 후보 모델 자체가 최소 성능에 미달
    if (
        candidate_accuracy
        < minimum_required_accuracy
    ):
        return ModelPromotionDecision(
            symbol=normalized_symbol,
            decision="REJECT",
            should_promote=False,

            candidate_model=candidate_model,
            candidate_balanced_accuracy=(
                candidate_accuracy
            ),

            current_model=current_model,
            current_balanced_accuracy=(
                current_accuracy
            ),

            best_historical_model=best_model,
            best_historical_balanced_accuracy=(
                best_accuracy
            ),

            improvement_over_current=(
                improvement_over_current
            ),

            improvement_over_best=(
                improvement_over_best
            ),

            minimum_required_accuracy=(
                minimum_required_accuracy
            ),

            minimum_improvement=(
                minimum_improvement
            ),

            reason=(
                "후보 모델의 Balanced Accuracy가 "
                f"최소 기준 {minimum_required_accuracy:.2f}%보다 "
                "낮습니다."
            ),
        )

    # 기존 저장 모델이 전혀 없는 최초 학습
    if current_accuracy is None:
        return ModelPromotionDecision(
            symbol=normalized_symbol,
            decision="FIRST_MODEL",
            should_promote=True,

            candidate_model=candidate_model,
            candidate_balanced_accuracy=(
                candidate_accuracy
            ),

            current_model=None,
            current_balanced_accuracy=None,

            best_historical_model=best_model,
            best_historical_balanced_accuracy=(
                best_accuracy
            ),

            improvement_over_current=None,
            improvement_over_best=(
                improvement_over_best
            ),

            minimum_required_accuracy=(
                minimum_required_accuracy
            ),

            minimum_improvement=(
                minimum_improvement
            ),

            reason=(
                "기존 저장 모델이 없어 후보 모델을 "
                "첫 번째 운영 모델로 저장할 수 있습니다."
            ),
        )

    # 역사상 최고 기록보다 성능이 낮은 경우
    if (
        best_accuracy is not None
        and candidate_accuracy
        < best_accuracy
    ):
        return ModelPromotionDecision(
            symbol=normalized_symbol,
            decision="KEEP_CURRENT",
            should_promote=False,

            candidate_model=candidate_model,
            candidate_balanced_accuracy=(
                candidate_accuracy
            ),

            current_model=current_model,
            current_balanced_accuracy=(
                current_accuracy
            ),

            best_historical_model=best_model,
            best_historical_balanced_accuracy=(
                best_accuracy
            ),

            improvement_over_current=(
                improvement_over_current
            ),

            improvement_over_best=(
                improvement_over_best
            ),

            minimum_required_accuracy=(
                minimum_required_accuracy
            ),

            minimum_improvement=(
                minimum_improvement
            ),

            reason=(
                "후보 모델이 역사상 최고 Balanced Accuracy보다 "
                "낮아 기존 모델을 유지합니다."
            ),
        )

    # 현재 모델보다 지정된 최소 개선 폭 이상 좋아짐
    if (
        improvement_over_current is not None
        and improvement_over_current
        >= minimum_improvement
    ):
        return ModelPromotionDecision(
            symbol=normalized_symbol,
            decision="PROMOTE",
            should_promote=True,

            candidate_model=candidate_model,
            candidate_balanced_accuracy=(
                candidate_accuracy
            ),

            current_model=current_model,
            current_balanced_accuracy=(
                current_accuracy
            ),

            best_historical_model=best_model,
            best_historical_balanced_accuracy=(
                best_accuracy
            ),

            improvement_over_current=(
                improvement_over_current
            ),

            improvement_over_best=(
                improvement_over_best
            ),

            minimum_required_accuracy=(
                minimum_required_accuracy
            ),

            minimum_improvement=(
                minimum_improvement
            ),

            reason=(
                "후보 모델이 현재 모델보다 "
                f"{improvement_over_current:.2f}%p 개선되어 "
                "교체 기준을 충족합니다."
            ),
        )

    return ModelPromotionDecision(
        symbol=normalized_symbol,
        decision="KEEP_CURRENT",
        should_promote=False,

        candidate_model=candidate_model,
        candidate_balanced_accuracy=(
            candidate_accuracy
        ),

        current_model=current_model,
        current_balanced_accuracy=(
            current_accuracy
        ),

        best_historical_model=best_model,
        best_historical_balanced_accuracy=(
            best_accuracy
        ),

        improvement_over_current=(
            improvement_over_current
        ),

        improvement_over_best=(
            improvement_over_best
        ),

        minimum_required_accuracy=(
            minimum_required_accuracy
        ),

        minimum_improvement=(
            minimum_improvement
        ),

        reason=(
            "후보 모델의 개선 폭이 "
            f"필요 기준 {minimum_improvement:.2f}%p보다 "
            "작아 기존 모델을 유지합니다."
        ),
    )


def print_promotion_decision(
    decision: ModelPromotionDecision,
) -> None:
    """
    모델 교체 판단 결과를 터미널에 출력합니다.
    """

    print()
    print("=" * 82)
    print(
        f"{decision.symbol} MODEL PROMOTION DECISION V4.7"
    )
    print("=" * 82)

    print(
        f"Decision            : "
        f"{decision.decision}"
    )

    print(
        f"Promote model       : "
        f"{decision.should_promote}"
    )

    print()
    print(
        f"Candidate model     : "
        f"{decision.candidate_model}"
    )

    print(
        f"Candidate bal. acc. : "
        f"{decision.candidate_balanced_accuracy:.2f}%"
    )

    print()
    print(
        f"Current model       : "
        f"{decision.current_model or 'N/A'}"
    )

    if (
        decision.current_balanced_accuracy
        is None
    ):
        print(
            "Current bal. acc.    : N/A"
        )

    else:
        print(
            f"Current bal. acc.    : "
            f"{decision.current_balanced_accuracy:.2f}%"
        )

    print()
    print(
        f"Best history model  : "
        f"{decision.best_historical_model or 'N/A'}"
    )

    if (
        decision
        .best_historical_balanced_accuracy
        is None
    ):
        print(
            "Best history acc.   : N/A"
        )

    else:
        print(
            f"Best history acc.   : "
            f"{decision.best_historical_balanced_accuracy:.2f}%"
        )

    print()

    if (
        decision.improvement_over_current
        is None
    ):
        print(
            "Change vs current   : N/A"
        )

    else:
        print(
            f"Change vs current   : "
            f"{decision.improvement_over_current:+.2f}%p"
        )

    if (
        decision.improvement_over_best
        is None
    ):
        print(
            "Change vs best      : N/A"
        )

    else:
        print(
            f"Change vs best      : "
            f"{decision.improvement_over_best:+.2f}%p"
        )

    print()
    print(
        f"Minimum accuracy    : "
        f"{decision.minimum_required_accuracy:.2f}%"
    )

    print(
        f"Required improvement: "
        f"{decision.minimum_improvement:.2f}%p"
    )

    print()
    print(
        f"Reason              : "
        f"{decision.reason}"
    )

    print("=" * 82)