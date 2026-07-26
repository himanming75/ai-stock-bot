from config import SYMBOLS

from automation.batch_trainer import (
    auto_train_symbols,
)


def main() -> None:
    """
    V5.1 다중 종목 자동 재학습 테스트입니다.
    """

    print()
    print("=" * 80)
    print(
        "AI STOCK BOT V5.1 "
        "BATCH TRAINER TEST"
    )
    print("=" * 80)

    try:
        report = auto_train_symbols(
            symbols=SYMBOLS,

            period="5y",
            interval="1d",

            horizon_days=5,
            minimum_return=0.0,

            minimum_required_accuracy=50.0,
            minimum_improvement=0.50,

            # 한 종목에서 실패해도
            # 다음 종목을 계속 처리합니다.
            continue_on_error=True,

            # output 폴더에 JSON 저장
            save_report=True,
        )

        summary = report[
            "summary"
        ]

        print()
        print("=" * 80)
        print(
            "V5.1 BATCH TRAINER "
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
            f"Promoted            : "
            f"{summary['promoted_count']}"
        )

        print(
            f"First models        : "
            f"{summary['first_model_count']}"
        )

        print(
            f"Current models kept : "
            f"{summary['kept_count']}"
        )

        print(
            f"Rejected            : "
            f"{summary['rejected_count']}"
        )

        print(
            f"Report file         : "
            f"{report['report_path']}"
        )

        print("=" * 80)

        print()
        print(
            "V5.1 batch trainer test "
            "completed successfully."
        )

    except KeyboardInterrupt:
        print()
        print(
            "사용자가 테스트를 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 80)
        print(
            "V5.1 BATCH TRAINER ERROR"
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