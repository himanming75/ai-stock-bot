from automation.daily_pipeline import (
    run_daily_pipeline,
)
from config import SYMBOLS


def main() -> None:
    """
    V6.1 Daily Automation Pipeline 테스트입니다.

    테스트 순서:

    1. Daily Prediction 실행
    2. Prediction Tracker 실행
    3. Recommendation Engine 실행
    4. Pipeline 결과 확인
    5. JSON 및 로그 파일 경로 확인
    """

    print()
    print("=" * 88)
    print(
        "AI STOCK BOT V6.1 "
        "DAILY PIPELINE TEST"
    )
    print("=" * 88)

    try:
        report = run_daily_pipeline(
            symbols=SYMBOLS,

            prediction_period="5y",
            prediction_interval="1d",

            # 실제 수익률이 -1%~+1%이면
            # NEUTRAL로 판정합니다.
            neutral_threshold_percent=1.0,

            # 한 단계에서 오류가 발생해도
            # 다음 단계를 가능한 범위에서 계속합니다.
            continue_after_step_error=True,
        )

        summary = report.get(
            "summary",
            {},
        )

        prediction_summary = report.get(
            "prediction_summary",
            {},
        )

        tracker_summary = report.get(
            "tracker_summary",
            {},
        )

        recommendation_summary = report.get(
            "recommendation_summary",
            {},
        )

        files = report.get(
            "files",
            {},
        )

        print()
        print("=" * 88)
        print(
            "V6.1 DAILY PIPELINE "
            "TEST RESULT"
        )
        print("=" * 88)

        print(
            f"Pipeline status       : "
            f"{summary.get('pipeline_status', 'UNKNOWN')}"
        )

        print(
            f"Total steps           : "
            f"{summary.get('total_steps', 0)}"
        )

        print(
            f"Successful steps      : "
            f"{summary.get('successful_steps', 0)}"
        )

        print(
            f"Failed steps          : "
            f"{summary.get('failed_steps', 0)}"
        )

        print()
        print("DAILY PREDICTIONS")
        print("-" * 88)

        print(
            f"Predictions success   : "
            f"{prediction_summary.get('successful_count', 0)}"
        )

        print(
            f"Predictions failed    : "
            f"{prediction_summary.get('failed_count', 0)}"
        )

        print(
            f"Bullish predictions   : "
            f"{prediction_summary.get('bullish_count', 0)}"
        )

        print(
            f"Neutral predictions   : "
            f"{prediction_summary.get('neutral_count', 0)}"
        )

        print(
            f"Bearish predictions   : "
            f"{prediction_summary.get('bearish_count', 0)}"
        )

        top_prediction_symbol = (
            prediction_summary.get(
                "top_symbol"
            )
        )

        top_up_probability = (
            prediction_summary.get(
                "top_up_probability"
            )
        )

        if (
            top_prediction_symbol is not None
            and top_up_probability is not None
        ):
            print(
                f"Top probability       : "
                f"{top_prediction_symbol} "
                f"{float(top_up_probability):.2f}%"
            )

        else:
            print(
                "Top probability       : N/A"
            )

        print()
        print("PREDICTION TRACKER")
        print("-" * 88)

        print(
            f"New history records   : "
            f"{tracker_summary.get('new_records', 0)}"
        )

        print(
            f"Duplicates skipped    : "
            f"{tracker_summary.get('duplicates_skipped', 0)}"
        )

        print(
            f"Evaluated now         : "
            f"{tracker_summary.get('evaluated_now', 0)}"
        )

        print(
            f"Completed predictions : "
            f"{tracker_summary.get('completed_total', 0)}"
        )

        print(
            f"Pending predictions   : "
            f"{tracker_summary.get('pending_total', 0)}"
        )

        print(
            f"Correct predictions   : "
            f"{tracker_summary.get('correct_total', 0)}"
        )

        print(
            f"Wrong predictions     : "
            f"{tracker_summary.get('wrong_total', 0)}"
        )

        print(
            f"Overall accuracy      : "
            f"{float(tracker_summary.get('overall_accuracy', 0.0)):.2f}%"
        )

        print()
        print("RECOMMENDATION ENGINE")
        print("-" * 88)

        print(
            f"Recommendations OK    : "
            f"{recommendation_summary.get('successful_count', 0)}"
        )

        print(
            f"Recommendations failed: "
            f"{recommendation_summary.get('failed_count', 0)}"
        )

        print(
            f"Strong Buy            : "
            f"{recommendation_summary.get('strong_buy_count', 0)}"
        )

        print(
            f"Buy                   : "
            f"{recommendation_summary.get('buy_count', 0)}"
        )

        print(
            f"Watch Buy             : "
            f"{recommendation_summary.get('watch_buy_count', 0)}"
        )

        print(
            f"Hold                  : "
            f"{recommendation_summary.get('hold_count', 0)}"
        )

        print(
            f"Avoid                 : "
            f"{recommendation_summary.get('avoid_count', 0)}"
        )

        print(
            f"Top symbol            : "
            f"{recommendation_summary.get('top_symbol') or 'N/A'}"
        )

        print(
            f"Top recommendation    : "
            f"{recommendation_summary.get('top_recommendation') or 'N/A'}"
        )

        top_score = recommendation_summary.get(
            "top_score"
        )

        if top_score is not None:
            print(
                f"Top score             : "
                f"{float(top_score):.2f}/100"
            )

        else:
            print(
                "Top score             : N/A"
            )

        print()
        print("FILES")
        print("-" * 88)

        print(
            f"Pipeline report       : "
            f"{files.get('pipeline_report') or 'N/A'}"
        )

        print(
            f"Latest pipeline       : "
            f"{files.get('latest_pipeline_report') or 'N/A'}"
        )

        print(
            f"Recommendation report : "
            f"{files.get('recommendation_report') or 'N/A'}"
        )

        print(
            f"Latest recommendation : "
            f"{files.get('latest_recommendation_report') or 'N/A'}"
        )

        print(
            f"Log file              : "
            f"{files.get('log_file') or 'N/A'}"
        )

        print("=" * 88)

        pipeline_status = summary.get(
            "pipeline_status"
        )

        failed_steps = int(
            summary.get(
                "failed_steps",
                0,
            )
        )

        if (
            pipeline_status == "SUCCESS"
            and failed_steps == 0
        ):
            print()
            print(
                "V6.1 daily pipeline test "
                "completed successfully."
            )

        else:
            print()
            print(
                "V6.1 daily pipeline test completed, "
                "but one or more steps require review."
            )

    except KeyboardInterrupt:
        print()
        print("=" * 88)
        print("TEST CANCELLED")
        print("=" * 88)

        print(
            "사용자가 테스트 실행을 중단했습니다."
        )

    except Exception as error:
        print()
        print("=" * 88)
        print(
            "V6.1 DAILY PIPELINE ERROR"
        )
        print("=" * 88)

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