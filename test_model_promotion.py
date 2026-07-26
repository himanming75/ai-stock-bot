from data.market import get_history
from ml.model_promotion import (
    evaluate_model_promotion,
    print_promotion_decision,
)
from ml.model_selector import (
    compare_models,
    print_model_comparison,
)


def main() -> None:
    """
    V4.7 모델 교체 판단 테스트입니다.
    """

    symbol = "AAPL"

    print()
    print("=" * 82)
    print("AI STOCK BOT V4.7 MODEL PROMOTION TEST")
    print("=" * 82)

    data = get_history(
        symbol=symbol,
        period="5y",
        interval="1d",
    )

    if data is None or data.empty:
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
        selection_result = compare_models(
            symbol=symbol,
            data=data,
            horizon_days=5,
            minimum_return=0.0,
        )

        print_model_comparison(
            selection_result
        )

        decision = evaluate_model_promotion(
            symbol=symbol,
            selection_result=selection_result,

            # 후보 모델이 적어도 50%는 넘어야 합니다.
            minimum_required_accuracy=50.0,

            # 현재 모델보다 최소 0.50%p 이상
            # 좋아야 자동 교체 후보가 됩니다.
            minimum_improvement=0.50,
        )

        print_promotion_decision(
            decision
        )

        print()
        print(
            "주의: 이번 테스트는 교체 여부만 판단하며 "
            "실제 모델 파일은 변경하지 않습니다."
        )

    except Exception as error:
        print()
        print("=" * 82)
        print("MODEL PROMOTION TEST ERROR")
        print("=" * 82)

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