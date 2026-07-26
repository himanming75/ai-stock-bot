from automation.prediction_tracker import (
    run_prediction_tracker,
)


def main() -> None:
    """
    V5.3 예측 이력 및 정확도 추적 테스트입니다.
    """

    print()
    print("=" * 80)
    print(
        "AI STOCK BOT V5.3 "
        "PREDICTION TRACKER TEST"
    )
    print("=" * 80)

    try:
        result = run_prediction_tracker(
            # 실제 등락률이 -1%~+1%이면
            # NEUTRAL로 판정합니다.
            neutral_threshold_percent=1.0,
        )

        append_result = result[
            "append_result"
        ]

        evaluation_result = result[
            "evaluation_result"
        ]

        accuracy_summary = result[
            "accuracy_report"
        ][
            "summary"
        ]

        files = result[
            "files"
        ]

        print()
        print("=" * 80)
        print(
            "V5.3 PREDICTION TRACKER "
            "TEST RESULT"
        )
        print("=" * 80)

        print(
            f"New records         : "
            f"{append_result['added_count']}"
        )

        print(
            f"Duplicates skipped  : "
            f"{append_result['skipped_count']}"
        )

        print(
            f"Evaluated now       : "
            f"{evaluation_result['evaluated_count']}"
        )

        print(
            f"Completed total     : "
            f"{accuracy_summary['completed_count']}"
        )

        print(
            f"Pending total       : "
            f"{accuracy_summary['pending_count']}"
        )

        print(
            f"Correct total       : "
            f"{accuracy_summary['correct_count']}"
        )

        print(
            f"Wrong total         : "
            f"{accuracy_summary['wrong_count']}"
        )

        print(
            f"Overall accuracy    : "
            f"{accuracy_summary['accuracy_percent']:.2f}%"
        )

        print(
            f"History JSON        : "
            f"{files['history_json']}"
        )

        print(
            f"History CSV         : "
            f"{files['history_csv']}"
        )

        print(
            f"Accuracy report     : "
            f"{files['accuracy_report']}"
        )

        print("=" * 80)

        print()
        print(
            "V5.3 prediction tracker test "
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
            "V5.3 PREDICTION TRACKER ERROR"
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