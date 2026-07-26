import json
from datetime import datetime
from pathlib import Path
from typing import Any

from automation.auto_trainer import (
    auto_train_symbol,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIRECTORY = PROJECT_ROOT / "output"

DEFAULT_REPORT_NAME = (
    "auto_training_report.json"
)


def normalize_symbols(
    symbols: list[str],
) -> list[str]:
    """
    종목 코드를 대문자로 정리하고
    빈 값과 중복 종목을 제거합니다.
    """

    cleaned_symbols: list[str] = []

    for symbol in symbols:
        normalized_symbol = (
            str(symbol)
            .upper()
            .strip()
        )

        if not normalized_symbol:
            continue

        if (
            normalized_symbol
            not in cleaned_symbols
        ):
            cleaned_symbols.append(
                normalized_symbol
            )

    return cleaned_symbols


def ensure_output_directory() -> Path:
    """
    output 폴더가 없으면 생성합니다.
    """

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    return OUTPUT_DIRECTORY


def save_batch_training_report(
    report: dict[str, Any],
    filename: str = DEFAULT_REPORT_NAME,
) -> Path:
    """
    다중 종목 자동 학습 결과를
    JSON 파일로 저장합니다.
    """

    output_directory = (
        ensure_output_directory()
    )

    report_path = (
        output_directory
        / filename
    )

    with report_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    return report_path


def build_symbol_summary(
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    auto_train_symbol의 전체 결과에서
    요약 정보만 추출합니다.
    """

    promotion = result.get(
        "promotion_decision",
        {},
    )

    backup_result = result.get(
        "backup_result"
    )

    saved_model_info = result.get(
        "saved_model_info"
    )

    return {
        "symbol": result.get(
            "symbol",
            "UNKNOWN",
        ),

        "status": result.get(
            "status",
            "UNKNOWN",
        ),

        "promotion_decision": (
            promotion.get(
                "decision",
                "UNKNOWN",
            )
        ),

        "should_promote": bool(
            promotion.get(
                "should_promote",
                False,
            )
        ),

        "candidate_model": (
            promotion.get(
                "candidate_model",
                "UNKNOWN",
            )
        ),

        "candidate_balanced_accuracy": (
            promotion.get(
                "candidate_balanced_accuracy",
                0.0,
            )
        ),

        "current_model": (
            promotion.get(
                "current_model"
            )
        ),

        "current_balanced_accuracy": (
            promotion.get(
                "current_balanced_accuracy"
            )
        ),

        "improvement_over_current": (
            promotion.get(
                "improvement_over_current"
            )
        ),

        "backup_created": bool(
            backup_result
            and backup_result.get(
                "backup_created",
                False,
            )
        ),

        "model_saved": (
            saved_model_info is not None
        ),

        "elapsed_seconds": result.get(
            "elapsed_seconds",
            0.0,
        ),
    }


def auto_train_symbols(
    symbols: list[str],
    period: str = "5y",
    interval: str = "1d",
    horizon_days: int = 5,
    minimum_return: float = 0.0,
    minimum_required_accuracy: float = 50.0,
    minimum_improvement: float = 0.50,
    continue_on_error: bool = True,
    save_report: bool = True,
) -> dict[str, Any]:
    """
    여러 종목을 차례대로 자동 재학습합니다.

    각 종목마다:

    1. 최신 데이터 다운로드
    2. 후보 모델 비교
    3. 기존 모델과 성능 비교
    4. 필요하면 기존 모델 백업
    5. 조건 충족 시 새 모델 저장
    6. 결과 기록

    continue_on_error=True이면 한 종목에서 오류가
    발생해도 나머지 종목은 계속 처리합니다.
    """

    cleaned_symbols = normalize_symbols(
        symbols
    )

    if not cleaned_symbols:
        raise ValueError(
            "자동 학습할 종목이 없습니다."
        )

    started_at = datetime.now()

    print()
    print("=" * 88)
    print(
        "AI STOCK BOT V5.1 "
        "MULTI-SYMBOL AUTO TRAINER"
    )
    print("=" * 88)

    print(
        f"Started at          : "
        f"{started_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        f"Symbols             : "
        f"{', '.join(cleaned_symbols)}"
    )

    print(
        f"Total symbols       : "
        f"{len(cleaned_symbols)}"
    )

    print(
        f"Minimum accuracy    : "
        f"{minimum_required_accuracy:.2f}%"
    )

    print(
        f"Required improvement: "
        f"{minimum_improvement:.2f}%p"
    )

    print("=" * 88)

    successful_results: list[
        dict[str, Any]
    ] = []

    failed_results: list[
        dict[str, Any]
    ] = []

    full_results: dict[
        str,
        dict[str, Any]
    ] = {}

    total_symbols = len(
        cleaned_symbols
    )

    for index, symbol in enumerate(
        cleaned_symbols,
        start=1,
    ):
        print()
        print("#" * 88)

        print(
            f"[{index}/{total_symbols}] "
            f"{symbol}"
        )

        print("#" * 88)

        symbol_started_at = (
            datetime.now()
        )

        try:
            result = auto_train_symbol(
                symbol=symbol,
                period=period,
                interval=interval,
                horizon_days=horizon_days,
                minimum_return=(
                    minimum_return
                ),
                minimum_required_accuracy=(
                    minimum_required_accuracy
                ),
                minimum_improvement=(
                    minimum_improvement
                ),
            )

            summary = build_symbol_summary(
                result
            )

            successful_results.append(
                summary
            )

            full_results[symbol] = {
                "success": True,
                "result": result,
                "error": None,
            }

        except KeyboardInterrupt:
            print()
            print(
                "사용자가 다중 종목 자동 학습을 "
                "중단했습니다."
            )

            raise

        except Exception as error:
            symbol_finished_at = (
                datetime.now()
            )

            elapsed_seconds = (
                symbol_finished_at
                - symbol_started_at
            ).total_seconds()

            error_result = {
                "symbol": symbol,

                "error_type": (
                    type(error).__name__
                ),

                "error_message": str(
                    error
                ),

                "started_at": (
                    symbol_started_at
                    .isoformat()
                ),

                "finished_at": (
                    symbol_finished_at
                    .isoformat()
                ),

                "elapsed_seconds": round(
                    elapsed_seconds,
                    2,
                ),
            }

            failed_results.append(
                error_result
            )

            full_results[symbol] = {
                "success": False,
                "result": None,
                "error": error_result,
            }

            print()
            print("=" * 88)
            print(
                f"{symbol} AUTO TRAINING FAILED"
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

            if not continue_on_error:
                raise

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    promoted_count = sum(
        1
        for item in successful_results
        if item.get(
            "should_promote",
            False,
        )
    )

    kept_count = sum(
        1
        for item in successful_results
        if item.get(
            "promotion_decision"
        )
        == "KEEP_CURRENT"
    )

    rejected_count = sum(
        1
        for item in successful_results
        if item.get(
            "promotion_decision"
        )
        == "REJECT"
    )

    first_model_count = sum(
        1
        for item in successful_results
        if item.get(
            "promotion_decision"
        )
        == "FIRST_MODEL"
    )

    report: dict[str, Any] = {
        "version": "V5.1",

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

        "settings": {
            "symbols": cleaned_symbols,
            "period": period,
            "interval": interval,
            "horizon_days": (
                horizon_days
            ),
            "minimum_return": (
                minimum_return
            ),
            "minimum_required_accuracy": (
                minimum_required_accuracy
            ),
            "minimum_improvement": (
                minimum_improvement
            ),
            "continue_on_error": (
                continue_on_error
            ),
        },

        "summary": {
            "total_symbols": (
                len(cleaned_symbols)
            ),

            "successful_count": (
                len(successful_results)
            ),

            "failed_count": (
                len(failed_results)
            ),

            "promoted_count": (
                promoted_count
            ),

            "first_model_count": (
                first_model_count
            ),

            "kept_count": (
                kept_count
            ),

            "rejected_count": (
                rejected_count
            ),
        },

        "successful_results": (
            successful_results
        ),

        "failed_results": (
            failed_results
        ),

        "full_results": (
            full_results
        ),
    }

    report_path: Path | None = None

    if save_report:
        report_path = (
            save_batch_training_report(
                report=report
            )
        )

        report[
            "report_path"
        ] = str(
            report_path
        )

    else:
        report[
            "report_path"
        ] = None

    print_batch_training_summary(
        report
    )

    return report


def print_batch_training_summary(
    report: dict[str, Any],
) -> None:
    """
    다중 종목 자동 학습 결과를
    표 형태로 출력합니다.
    """

    summary = report.get(
        "summary",
        {},
    )

    results = report.get(
        "successful_results",
        [],
    )

    failures = report.get(
        "failed_results",
        [],
    )

    print()
    print("=" * 110)

    print(
        "AI STOCK BOT V5.1 "
        "AUTO TRAINING SUMMARY"
    )

    print("=" * 110)

    print(
        f"Total symbols       : "
        f"{summary.get('total_symbols', 0)}"
    )

    print(
        f"Successful          : "
        f"{summary.get('successful_count', 0)}"
    )

    print(
        f"Failed              : "
        f"{summary.get('failed_count', 0)}"
    )

    print(
        f"Promoted            : "
        f"{summary.get('promoted_count', 0)}"
    )

    print(
        f"First models        : "
        f"{summary.get('first_model_count', 0)}"
    )

    print(
        f"Current models kept : "
        f"{summary.get('kept_count', 0)}"
    )

    print(
        f"Rejected            : "
        f"{summary.get('rejected_count', 0)}"
    )

    print(
        f"Elapsed time        : "
        f"{report.get('elapsed_seconds', 0.0):.2f} seconds"
    )

    print()

    print(
        f"{'No.':<5}"
        f"{'Symbol':<10}"
        f"{'Decision':<16}"
        f"{'Candidate':<22}"
        f"{'Candidate Acc.':>16}"
        f"{'Current Acc.':>15}"
        f"{'Change':>12}"
        f"{'Saved':>10}"
    )

    print("-" * 110)

    for index, item in enumerate(
        results,
        start=1,
    ):
        candidate_accuracy = float(
            item.get(
                "candidate_balanced_accuracy",
                0.0,
            )
        )

        current_accuracy_value = (
            item.get(
                "current_balanced_accuracy"
            )
        )

        if current_accuracy_value is None:
            current_accuracy_text = (
                "N/A"
            )

        else:
            current_accuracy_text = (
                f"{float(current_accuracy_value):.2f}%"
            )

        improvement_value = (
            item.get(
                "improvement_over_current"
            )
        )

        if improvement_value is None:
            improvement_text = "N/A"

        else:
            improvement_text = (
                f"{float(improvement_value):+.2f}%p"
            )

        model_saved_text = (
            "YES"
            if item.get(
                "model_saved",
                False,
            )
            else "NO"
        )

        print(
            f"{index:<5}"
            f"{str(item.get('symbol', '')):<10}"
            f"{str(item.get('promotion_decision', '')):<16}"
            f"{str(item.get('candidate_model', '')):<22}"
            f"{candidate_accuracy:>15.2f}%"
            f"{current_accuracy_text:>15}"
            f"{improvement_text:>12}"
            f"{model_saved_text:>10}"
        )

    print("-" * 110)

    if failures:
        print()
        print("FAILED SYMBOLS")
        print("-" * 110)

        for failure in failures:
            print(
                f"{failure.get('symbol', 'UNKNOWN')}: "
                f"{failure.get('error_type', 'Error')} - "
                f"{failure.get('error_message', '')}"
            )

    report_path = report.get(
        "report_path"
    )

    print()

    print(
        f"JSON report         : "
        f"{report_path or 'Not saved'}"
    )

    print("=" * 110)