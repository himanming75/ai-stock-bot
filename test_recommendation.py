from recommendation.engine import (
    generate_recommendations,
)


def main() -> None:
    """
    AI Stock Bot V6.0 Recommendation Engine 테스트입니다.
    """

    print()
    print("=" * 80)
    print(
        "AI STOCK BOT V6.0 "
        "RECOMMENDATION ENGINE TEST"
    )
    print("=" * 80)

    try:
        report = generate_recommendations()

        summary = report[
            "summary"
        ]

        files = report[
            "files"
        ]

        print()
        print("=" * 80)
        print(
            "V6.0 RECOMMENDATION "
            "TEST RESULT"
        )
        print("=" * 80)

        print(
            f"Successful results : "
            f"{summary['successful_count']}"
        )

        print(
            f"Failed results     : "
            f"{summary['failed_count']}"
        )

        print(
            f"Top symbol         : "
            f"{summary['top_symbol'] or 'N/A'}"
        )

        print(
            f"Top recommendation : "
            f"{summary['top_recommendation'] or 'N/A'}"
        )

        top_score = summary.get(
            "top_score"
        )

        if top_score is not None:
            print(
                f"Top score          : "
                f"{float(top_score):.2f}/100"
            )

        else:
            print(
                "Top score          : N/A"
            )

        print(
            f"Report file        : "
            f"{files['report_path']}"
        )

        print(
            f"Latest file        : "
            f"{files['latest_path']}"
        )

        print("=" * 80)

        print()
        print(
            "V6.0 recommendation engine test "
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
            "V6.0 RECOMMENDATION ENGINE ERROR"
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