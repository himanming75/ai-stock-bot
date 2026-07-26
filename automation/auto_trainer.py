from dataclasses import asdict
from datetime import datetime
from typing import Any

from data.market import get_history
from ml.model_promotion import (
    evaluate_model_promotion,
    print_promotion_decision,
)
from ml.model_registry import (
    active_model_exists,
    backup_active_model,
    print_backup_result,
)
from ml.model_selector import (
    compare_models,
    print_model_comparison,
)
from ml.model_trainer import (
    train_and_save_best_model,
)


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


def auto_train_symbol(
    symbol: str,
    period: str = "5y",
    interval: str = "1d",
    horizon_days: int = 5,
    minimum_return: float = 0.0,
    minimum_required_accuracy: float = 50.0,
    minimum_improvement: float = 0.50,
) -> dict[str, Any]:
    """
    한 종목의 자동 재학습을 실행합니다.

    실행 순서:

    1. 최신 시장 데이터 다운로드
    2. 후보 모델 비교
    3. 기존 모델과 성능 비교
    4. 교체 필요 여부 판단
    5. 기존 모델 백업
    6. 새 모델 학습 및 저장
    7. 결과 반환
    """

    normalized_symbol = normalize_symbol(
        symbol
    )

    started_at = datetime.now()

    print()
    print("=" * 82)
    print(
        f"AUTO TRAINING "
        f"{normalized_symbol} V5.0"
    )
    print("=" * 82)

    print(
        f"Started at          : "
        f"{started_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        f"History period      : "
        f"{period}"
    )

    print(
        f"Prediction horizon  : "
        f"{horizon_days} trading days"
    )

    print(
        f"Minimum accuracy    : "
        f"{minimum_required_accuracy:.2f}%"
    )

    print(
        f"Required improvement: "
        f"{minimum_improvement:.2f}%p"
    )

    print()
    print(
        f"Downloading "
        f"{normalized_symbol} market data..."
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

    print(
        f"Downloaded rows     : "
        f"{len(data)}"
    )

    print()
    print(
        "Comparing candidate models..."
    )

    # 새 후보 모델들을 비교합니다.
    # 이 단계에서는 운영 모델을 저장하거나
    # 교체하지 않습니다.
    selection_result = compare_models(
        symbol=normalized_symbol,
        data=data,
        horizon_days=horizon_days,
        minimum_return=minimum_return,
    )

    print_model_comparison(
        selection_result
    )

    # 새 후보 모델과 현재 운영 모델의
    # 검증 성능을 비교합니다.
    promotion_decision = (
        evaluate_model_promotion(
            symbol=normalized_symbol,
            selection_result=selection_result,
            minimum_required_accuracy=(
                minimum_required_accuracy
            ),
            minimum_improvement=(
                minimum_improvement
            ),
        )
    )

    print_promotion_decision(
        promotion_decision
    )

    active_model_before = (
        active_model_exists(
            normalized_symbol
        )
    )

    backup_result = None
    saved_model_info = None

    if promotion_decision.should_promote:
        print()
        print("=" * 82)
        print("MODEL PROMOTION APPROVED")
        print("=" * 82)

        # 기존 운영 모델이 있으면
        # 새 모델 저장 전에 백업합니다.
        if active_model_before:
            print(
                "Backing up current active model..."
            )

            backup_result = backup_active_model(
                normalized_symbol
            )

            print_backup_result(
                backup_result
            )

        else:
            print(
                "기존 운영 모델이 없어 "
                "백업을 건너뜁니다."
            )

        print()
        print(
            "Training and saving promoted model..."
        )

        # 교체 승인을 받은 경우에만
        # 실제 모델 파일을 저장합니다.
        saved_model_info = (
            train_and_save_best_model(
                symbol=normalized_symbol,
                data=data,
                horizon_days=horizon_days,
                minimum_return=minimum_return,
            )
        )

        final_status = "MODEL_PROMOTED"

    else:
        print()
        print("=" * 82)
        print("CURRENT MODEL RETAINED")
        print("=" * 82)

        print(
            "후보 모델이 교체 기준을 충족하지 않아 "
            "현재 운영 모델을 유지합니다."
        )

        print(
            "기존 모델 파일과 메타데이터는 "
            "변경되지 않았습니다."
        )

        final_status = "CURRENT_MODEL_KEPT"

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at - started_at
    ).total_seconds()

    result = {
        "symbol": normalized_symbol,

        "status": final_status,

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

        "downloaded_rows": int(
            len(data)
        ),

        "period": period,
        "interval": interval,

        "horizon_days": int(
            horizon_days
        ),

        "minimum_return": float(
            minimum_return
        ),

        "minimum_required_accuracy": float(
            minimum_required_accuracy
        ),

        "minimum_improvement": float(
            minimum_improvement
        ),

        "active_model_existed_before": (
            active_model_before
        ),

        "promotion_decision": (
            promotion_decision.to_dict()
        ),

        "selection_result": (
            selection_result.to_dict()
        ),

        "backup_result": (
            backup_result.to_dict()
            if backup_result is not None
            else None
        ),

        "saved_model_info": (
            saved_model_info.to_dict()
            if saved_model_info is not None
            else None
        ),
    }

    print()
    print("=" * 82)
    print(
        f"{normalized_symbol} AUTO TRAINING COMPLETED"
    )
    print("=" * 82)

    print(
        f"Final status        : "
        f"{final_status}"
    )

    print(
        f"Promotion decision  : "
        f"{promotion_decision.decision}"
    )

    print(
        f"Candidate model     : "
        f"{promotion_decision.candidate_model}"
    )

    print(
        f"Candidate bal. acc. : "
        f"{promotion_decision.candidate_balanced_accuracy:.2f}%"
    )

    if saved_model_info is not None:
        print(
            f"Saved model         : "
            f"{saved_model_info.model_name}"
        )

        print(
            f"Model file          : "
            f"{saved_model_info.model_path}"
        )

    else:
        print(
            "Saved model         : "
            "기존 운영 모델 유지"
        )

    print(
        f"Elapsed time        : "
        f"{elapsed_seconds:.2f} seconds"
    )

    print("=" * 82)

    return result