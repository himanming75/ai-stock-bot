from automation.daily_predictor import (
    generate_daily_predictions,
)
from config import SYMBOLS


def main() -> None:
    """
    V5.2 Daily Prediction Engine 테스트입니다.

    저장된 운영 모델이 존재하는 종목만
    정상적으로 예측됩니다.

    저장 모델이 없는 종목은 오류 결과로
    기록하고 다른 종목은 계속 실행합니다.
    """

    print()
    print("=" * 80)
    print(
        "AI STOCK BOT V5.2 "
        "DAILY PREDICTION TEST"
    )
    print("=" * 80)

    try:
        report = generate_daily_predictions(
            symbols=SYMBOLS,

            period="5y",
            interval="1d",

            # 일부 종목에 저장된 모델이 없어도
            # 다음 종목을 계속 처리합니다.
            continue_on_error=True,

            # JSON 및 CSV 저장
            save_reports=True,
        )

        summary = report[
            "summary"
        ]

        files = report[
            "files"
        ]

        print()
        print("=" * 80)
        print(
            "V5.2 DAILY PREDICTION "
            "TEST RESULT"
        )
        print("=" * 80)

        print(
            f"Total symbols       : "
            f"{summary['total_symbols']}"
        )

        print(
            f"Successful          : "
            f"{summary['successful_count']}"
        )

        print(
            f"Failed              : "
            f"{summary['failed_count']}"
        )

        print(
            f"Bullish             : "
            f"{summary['bullish_count']}"
        )

        print(
            f"Neutral             : "
            f"{summary['neutral_count']}"
        )

        print(
            f"Bearish             : "
            f"{summary['bearish_count']}"
        )

        print(
            f"Top symbol          : "
            f"{summary['top_symbol'] or 'N/A'}"
        )

        top_probability = (
            summary[
                "top_up_probability"
            ]
        )

        if top_probability is None:
            print(
                "Top up probability  : N/A"
            )

        else:
            print(
                f"Top up probability  : "
                f"{float(top_probability):.2f}%"
            )

        print(
            f"Latest JSON         : "
            f"{files['latest_json_report']}"
        )

        print(
            f"Latest CSV          : "
            f"{files['latest_csv_report']}"
        )

        print("=" * 80)

        print()
        print(
            "V5.2 daily prediction test "
            "completed successfully."
        )

    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("TEST CANCELLED")
        print("=" * 80)

        print(
            "사용자가 테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 80)
        print(
            "V5.2 DAILY PREDICTION ERROR"
        )
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