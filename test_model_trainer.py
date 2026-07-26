from data.market import get_history
from ml.model_history import (
    get_best_history_record,
    get_latest_history_record,
    print_model_history_summary,
)
from ml.model_trainer import (
    predict_with_saved_model,
    print_saved_prediction,
    train_and_save_best_model,
)


def main() -> None:
    """
    V4.6 Model Trainer 테스트 순서:

    1. AAPL 과거 데이터 다운로드
    2. 후보 모델 비교
    3. 최고 모델 학습 및 저장
    4. 모델 성능 이력 저장
    5. 저장된 모델 다시 불러오기
    6. 최신 예측 실행
    7. 전체 모델 이력 출력
    8. 최신 기록과 역사상 최고 기록 출력
    """

    symbol = "AAPL"

    print()
    print("=" * 80)
    print("AI STOCK BOT V4.6 MODEL TRAINER TEST")
    print("=" * 80)

    print(
        f"Downloading {symbol} market data..."
    )

    data = get_history(
        symbol=symbol,
        period="5y",
        interval="1d",
    )

    if data is None or data.empty:
        print()
        print(
            f"{symbol} 시장 데이터를 "
            "다운로드하지 못했습니다."
        )
        return

    print(
        f"Downloaded rows     : "
        f"{len(data)}"
    )

    try:
        # 1. 후보 모델 비교, 최고 모델 학습 및 저장
        saved_model_info = (
            train_and_save_best_model(
                symbol=symbol,
                data=data,
                horizon_days=5,
                minimum_return=0.0,
            )
        )

        print()
        print("=" * 80)
        print("SAVED MODEL INFORMATION")
        print("=" * 80)

        print(
            f"Symbol              : "
            f"{saved_model_info.symbol}"
        )

        print(
            f"Saved best model    : "
            f"{saved_model_info.model_name}"
        )

        print(
            f"Balanced accuracy   : "
            f"{saved_model_info.balanced_accuracy:.2f}%"
        )

        print(
            f"Validation accuracy : "
            f"{saved_model_info.validation_accuracy:.2f}%"
        )

        print(
            f"Latest prediction   : "
            f"{saved_model_info.latest_prediction}"
        )

        print(
            f"Latest up prob.     : "
            f"{saved_model_info.latest_upward_probability:.2f}%"
        )

        print(
            f"Ensemble prediction : "
            f"{saved_model_info.ensemble_prediction}"
        )

        print(
            f"Ensemble up prob.   : "
            f"{saved_model_info.ensemble_upward_probability:.2f}%"
        )

        print(
            f"Model status        : "
            f"{saved_model_info.selection_status}"
        )

        print(
            f"Model file          : "
            f"{saved_model_info.model_path}"
        )

        print(
            f"Metadata file       : "
            f"{saved_model_info.metadata_path}"
        )

        print(
            f"History file        : "
            f"{saved_model_info.history_path}"
        )

        # 2. 저장된 모델을 다시 불러와 최신 예측
        saved_prediction = (
            predict_with_saved_model(
                symbol=symbol,
                data=data,
            )
        )

        print_saved_prediction(
            saved_prediction
        )

        # 3. 누적된 모델 성능 이력 출력
        print_model_history_summary(
            symbol
        )

        # 4. 가장 최근 기록 확인
        latest_record = (
            get_latest_history_record(
                symbol
            )
        )

        # 5. 역사상 가장 높은 성능 기록 확인
        best_record = (
            get_best_history_record(
                symbol
            )
        )

        print()
        print("=" * 80)
        print("MODEL HISTORY CHECK")
        print("=" * 80)

        if latest_record is not None:
            print(
                f"Latest history model: "
                f"{latest_record.get('model_name', 'N/A')}"
            )

            print(
                f"Latest balanced acc.: "
                f"{float(latest_record.get('balanced_accuracy', 0.0)):.2f}%"
            )

            print(
                f"Latest recorded at  : "
                f"{latest_record.get('recorded_at', 'N/A')}"
            )

        else:
            print(
                "Latest history record: N/A"
            )

        print()

        if best_record is not None:
            print(
                f"Best history model  : "
                f"{best_record.get('model_name', 'N/A')}"
            )

            print(
                f"Best balanced acc.  : "
                f"{float(best_record.get('balanced_accuracy', 0.0)):.2f}%"
            )

            print(
                f"Best recorded at    : "
                f"{best_record.get('recorded_at', 'N/A')}"
            )

        else:
            print(
                "Best history record : N/A"
            )

        print("=" * 80)

        print()
        print(
            "V4.6 model trainer test "
            "completed successfully."
        )

    except FileNotFoundError as error:
        print()
        print("=" * 80)
        print("MODEL FILE ERROR")
        print("=" * 80)
        print(error)

    except ValueError as error:
        print()
        print("=" * 80)
        print("MODEL DATA ERROR")
        print("=" * 80)
        print(error)

    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("TEST CANCELLED")
        print("=" * 80)
        print(
            "사용자가 테스트 실행을 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 80)
        print("UNEXPECTED TEST ERROR")
        print("=" * 80)

        print(
            f"Error type   : "
            f"{type(error).__name__}"
        )

        print(
            f"Error message: "
            f"{error}"
        )


if __name__ == "__main__":
    main()