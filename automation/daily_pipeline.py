import json
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from automation.daily_predictor import (
    generate_daily_predictions,
)
from automation.prediction_tracker import (
    run_prediction_tracker,
)
from recommendation.engine import (
    generate_recommendations,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIRECTORY = PROJECT_ROOT / "output"
LOG_DIRECTORY = PROJECT_ROOT / "logs"

PIPELINE_REPORT_DIRECTORY = (
    OUTPUT_DIRECTORY
    / "pipeline_reports"
)

LATEST_PIPELINE_REPORT_PATH = (
    OUTPUT_DIRECTORY
    / "daily_pipeline_latest.json"
)


@dataclass
class PipelineStepResult:
    """
    Daily Pipeline의 한 단계 실행 결과입니다.
    """

    step_name: str
    success: bool

    started_at: str
    finished_at: str
    elapsed_seconds: float

    message: str
    result: dict[str, Any] | None

    error_type: str | None
    error_message: str | None
    traceback_text: str | None

    def to_dict(self) -> dict[str, Any]:
        """
        Dataclass를 JSON 저장이 가능한
        딕셔너리로 변환합니다.
        """

        return asdict(self)


def ensure_directories() -> None:
    """
    Pipeline 결과와 로그 저장 폴더를 생성합니다.
    """

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    LOG_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    PIPELINE_REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


def normalize_symbols(
    symbols: list[str],
) -> list[str]:
    """
    종목 코드를 대문자로 정리하고
    빈 값과 중복 값을 제거합니다.
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

        if normalized_symbol not in cleaned_symbols:
            cleaned_symbols.append(
                normalized_symbol
            )

    return cleaned_symbols


def save_json_file(
    path: Path,
    data: Any,
) -> None:
    """
    데이터를 JSON 파일로 저장합니다.
    """

    ensure_directories()

    with path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def append_log(
    message: str,
    log_path: Path,
) -> None:
    """
    실행 메시지를 로그 파일에 추가합니다.
    """

    ensure_directories()

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    line = (
        f"[{timestamp}] "
        f"{message}"
    )

    with log_path.open(
        mode="a",
        encoding="utf-8",
    ) as file:
        file.write(
            line + "\n"
        )


def build_daily_log_path(
    started_at: datetime,
) -> Path:
    """
    날짜별 로그 파일 경로를 생성합니다.
    """

    date_text = started_at.strftime(
        "%Y%m%d"
    )

    return (
        LOG_DIRECTORY
        / f"daily_pipeline_{date_text}.log"
    )


def create_skipped_step(
    step_name: str,
    reason: str,
) -> PipelineStepResult:
    """
    이전 단계 실패로 실행하지 않은
    Pipeline 단계 결과를 생성합니다.
    """

    skipped_at = datetime.now()

    return PipelineStepResult(
        step_name=step_name,
        success=False,

        started_at=(
            skipped_at.isoformat()
        ),

        finished_at=(
            skipped_at.isoformat()
        ),

        elapsed_seconds=0.0,

        message=(
            f"{step_name} skipped."
        ),

        result=None,

        error_type="SKIPPED",
        error_message=reason,
        traceback_text=None,
    )


def run_pipeline_step(
    step_name: str,
    function: Callable[..., Any],
    log_path: Path,
    **kwargs: Any,
) -> PipelineStepResult:
    """
    Pipeline의 한 단계를 안전하게 실행합니다.

    단계에서 오류가 발생해도 전체 프로그램을
    즉시 중단하지 않고 오류 내용을 기록합니다.
    """

    started_at = datetime.now()

    append_log(
        message=(
            f"STEP STARTED: {step_name}"
        ),
        log_path=log_path,
    )

    try:
        raw_result = function(
            **kwargs
        )

        if isinstance(
            raw_result,
            dict,
        ):
            result_data = raw_result

        elif hasattr(
            raw_result,
            "to_dict",
        ):
            result_data = (
                raw_result.to_dict()
            )

        else:
            result_data = {
                "value": str(
                    raw_result
                )
            }

        finished_at = datetime.now()

        elapsed_seconds = (
            finished_at
            - started_at
        ).total_seconds()

        append_log(
            message=(
                f"STEP COMPLETED: {step_name} "
                f"({elapsed_seconds:.2f} seconds)"
            ),
            log_path=log_path,
        )

        return PipelineStepResult(
            step_name=step_name,
            success=True,

            started_at=(
                started_at.isoformat()
            ),

            finished_at=(
                finished_at.isoformat()
            ),

            elapsed_seconds=round(
                elapsed_seconds,
                2,
            ),

            message=(
                f"{step_name} completed successfully."
            ),

            result=result_data,

            error_type=None,
            error_message=None,
            traceback_text=None,
        )

    except KeyboardInterrupt:
        append_log(
            message=(
                f"STEP CANCELLED: {step_name}"
            ),
            log_path=log_path,
        )

        raise

    except Exception as error:
        finished_at = datetime.now()

        elapsed_seconds = (
            finished_at
            - started_at
        ).total_seconds()

        traceback_text = (
            traceback.format_exc()
        )

        append_log(
            message=(
                f"STEP FAILED: {step_name} | "
                f"{type(error).__name__}: {error}"
            ),
            log_path=log_path,
        )

        return PipelineStepResult(
            step_name=step_name,
            success=False,

            started_at=(
                started_at.isoformat()
            ),

            finished_at=(
                finished_at.isoformat()
            ),

            elapsed_seconds=round(
                elapsed_seconds,
                2,
            ),

            message=(
                f"{step_name} failed."
            ),

            result=None,

            error_type=(
                type(error).__name__
            ),

            error_message=str(
                error
            ),

            traceback_text=(
                traceback_text
            ),
        )


def get_prediction_summary(
    prediction_step: PipelineStepResult,
) -> dict[str, Any]:
    """
    Daily Prediction 결과의 핵심 내용을 추출합니다.
    """

    if (
        not prediction_step.success
        or prediction_step.result is None
    ):
        return {
            "successful_count": 0,
            "failed_count": 0,
            "bullish_count": 0,
            "neutral_count": 0,
            "bearish_count": 0,
            "top_symbol": None,
            "top_up_probability": None,
        }

    summary = prediction_step.result.get(
        "summary",
        {},
    )

    return {
        "successful_count": summary.get(
            "successful_count",
            0,
        ),

        "failed_count": summary.get(
            "failed_count",
            0,
        ),

        "bullish_count": summary.get(
            "bullish_count",
            0,
        ),

        "neutral_count": summary.get(
            "neutral_count",
            0,
        ),

        "bearish_count": summary.get(
            "bearish_count",
            0,
        ),

        "top_symbol": summary.get(
            "top_symbol"
        ),

        "top_up_probability": summary.get(
            "top_up_probability"
        ),
    }


def get_tracker_summary(
    tracker_step: PipelineStepResult,
) -> dict[str, Any]:
    """
    Prediction Tracker 결과의 핵심 내용을 추출합니다.
    """

    if (
        not tracker_step.success
        or tracker_step.result is None
    ):
        return {
            "new_records": 0,
            "duplicates_skipped": 0,
            "evaluated_now": 0,
            "completed_total": 0,
            "pending_total": 0,
            "correct_total": 0,
            "wrong_total": 0,
            "overall_accuracy": 0.0,
        }

    append_result = (
        tracker_step.result.get(
            "append_result",
            {},
        )
    )

    evaluation_result = (
        tracker_step.result.get(
            "evaluation_result",
            {},
        )
    )

    accuracy_report = (
        tracker_step.result.get(
            "accuracy_report",
            {},
        )
    )

    accuracy_summary = (
        accuracy_report.get(
            "summary",
            {},
        )
    )

    return {
        "new_records": (
            append_result.get(
                "added_count",
                0,
            )
        ),

        "duplicates_skipped": (
            append_result.get(
                "skipped_count",
                0,
            )
        ),

        "evaluated_now": (
            evaluation_result.get(
                "evaluated_count",
                0,
            )
        ),

        "completed_total": (
            accuracy_summary.get(
                "completed_count",
                0,
            )
        ),

        "pending_total": (
            accuracy_summary.get(
                "pending_count",
                0,
            )
        ),

        "correct_total": (
            accuracy_summary.get(
                "correct_count",
                0,
            )
        ),

        "wrong_total": (
            accuracy_summary.get(
                "wrong_count",
                0,
            )
        ),

        "overall_accuracy": (
            accuracy_summary.get(
                "accuracy_percent",
                0.0,
            )
        ),
    }


def get_recommendation_summary(
    recommendation_step: PipelineStepResult,
) -> dict[str, Any]:
    """
    Recommendation Engine 결과의
    핵심 내용을 추출합니다.
    """

    if (
        not recommendation_step.success
        or recommendation_step.result is None
    ):
        return {
            "successful_count": 0,
            "failed_count": 0,

            "strong_buy_count": 0,
            "buy_count": 0,
            "watch_buy_count": 0,
            "hold_count": 0,
            "avoid_count": 0,

            "top_symbol": None,
            "top_recommendation": None,
            "top_score": None,

            "report_path": None,
            "latest_path": None,
        }

    summary = (
        recommendation_step.result.get(
            "summary",
            {},
        )
    )

    recommendation_counts = (
        summary.get(
            "recommendation_counts",
            {},
        )
    )

    files = (
        recommendation_step.result.get(
            "files",
            {},
        )
    )

    return {
        "successful_count": summary.get(
            "successful_count",
            0,
        ),

        "failed_count": summary.get(
            "failed_count",
            0,
        ),

        "strong_buy_count": (
            recommendation_counts.get(
                "STRONG_BUY",
                0,
            )
        ),

        "buy_count": (
            recommendation_counts.get(
                "BUY",
                0,
            )
        ),

        "watch_buy_count": (
            recommendation_counts.get(
                "WATCH_BUY",
                0,
            )
        ),

        "hold_count": (
            recommendation_counts.get(
                "HOLD",
                0,
            )
        ),

        "avoid_count": (
            recommendation_counts.get(
                "AVOID",
                0,
            )
        ),

        "top_symbol": summary.get(
            "top_symbol"
        ),

        "top_recommendation": summary.get(
            "top_recommendation"
        ),

        "top_score": summary.get(
            "top_score"
        ),

        "report_path": files.get(
            "report_path"
        ),

        "latest_path": files.get(
            "latest_path"
        ),
    }


def save_pipeline_report(
    report: dict[str, Any],
    finished_at: datetime,
) -> tuple[Path, Path]:
    """
    실행 시간별 보고서와 latest 보고서를 저장합니다.
    """

    ensure_directories()

    timestamp = finished_at.strftime(
        "%Y%m%d_%H%M%S"
    )

    dated_report_path = (
        PIPELINE_REPORT_DIRECTORY
        / f"daily_pipeline_{timestamp}.json"
    )

    save_json_file(
        path=dated_report_path,
        data=report,
    )

    save_json_file(
        path=LATEST_PIPELINE_REPORT_PATH,
        data=report,
    )

    return (
        dated_report_path,
        LATEST_PIPELINE_REPORT_PATH,
    )


def print_pipeline_summary(
    report: dict[str, Any],
) -> None:
    """
    Daily Pipeline 최종 요약을 출력합니다.
    """

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
    print("=" * 92)
    print(
        "AI STOCK BOT V6.1 "
        "DAILY AUTOMATION PIPELINE"
    )
    print("=" * 92)

    print(
        f"Pipeline status      : "
        f"{summary.get('pipeline_status', 'UNKNOWN')}"
    )

    print(
        f"Total steps          : "
        f"{summary.get('total_steps', 0)}"
    )

    print(
        f"Steps successful     : "
        f"{summary.get('successful_steps', 0)}"
    )

    print(
        f"Steps failed         : "
        f"{summary.get('failed_steps', 0)}"
    )

    print(
        f"Elapsed time         : "
        f"{float(report.get('elapsed_seconds', 0.0)):.2f} seconds"
    )

    print()
    print("DAILY PREDICTIONS")
    print("-" * 92)

    print(
        f"Successful symbols   : "
        f"{prediction_summary.get('successful_count', 0)}"
    )

    print(
        f"Failed symbols       : "
        f"{prediction_summary.get('failed_count', 0)}"
    )

    print(
        f"Bullish              : "
        f"{prediction_summary.get('bullish_count', 0)}"
    )

    print(
        f"Neutral              : "
        f"{prediction_summary.get('neutral_count', 0)}"
    )

    print(
        f"Bearish              : "
        f"{prediction_summary.get('bearish_count', 0)}"
    )

    top_symbol = prediction_summary.get(
        "top_symbol"
    )

    top_probability = prediction_summary.get(
        "top_up_probability"
    )

    if (
        top_symbol is not None
        and top_probability is not None
    ):
        print(
            f"Top probability      : "
            f"{top_symbol} "
            f"{float(top_probability):.2f}%"
        )

    else:
        print(
            "Top probability      : N/A"
        )

    print()
    print("PREDICTION TRACKER")
    print("-" * 92)

    print(
        f"New records          : "
        f"{tracker_summary.get('new_records', 0)}"
    )

    print(
        f"Duplicates skipped   : "
        f"{tracker_summary.get('duplicates_skipped', 0)}"
    )

    print(
        f"Evaluated now        : "
        f"{tracker_summary.get('evaluated_now', 0)}"
    )

    print(
        f"Completed total      : "
        f"{tracker_summary.get('completed_total', 0)}"
    )

    print(
        f"Pending total        : "
        f"{tracker_summary.get('pending_total', 0)}"
    )

    print(
        f"Correct total        : "
        f"{tracker_summary.get('correct_total', 0)}"
    )

    print(
        f"Wrong total          : "
        f"{tracker_summary.get('wrong_total', 0)}"
    )

    print(
        f"Overall accuracy     : "
        f"{float(tracker_summary.get('overall_accuracy', 0.0)):.2f}%"
    )

    print()
    print("RECOMMENDATION ENGINE")
    print("-" * 92)

    print(
        f"Successful results   : "
        f"{recommendation_summary.get('successful_count', 0)}"
    )

    print(
        f"Failed results       : "
        f"{recommendation_summary.get('failed_count', 0)}"
    )

    print(
        f"Strong Buy           : "
        f"{recommendation_summary.get('strong_buy_count', 0)}"
    )

    print(
        f"Buy                  : "
        f"{recommendation_summary.get('buy_count', 0)}"
    )

    print(
        f"Watch Buy            : "
        f"{recommendation_summary.get('watch_buy_count', 0)}"
    )

    print(
        f"Hold                 : "
        f"{recommendation_summary.get('hold_count', 0)}"
    )

    print(
        f"Avoid                : "
        f"{recommendation_summary.get('avoid_count', 0)}"
    )

    print(
        f"Top symbol           : "
        f"{recommendation_summary.get('top_symbol') or 'N/A'}"
    )

    print(
        f"Top recommendation   : "
        f"{recommendation_summary.get('top_recommendation') or 'N/A'}"
    )

    top_score = recommendation_summary.get(
        "top_score"
    )

    if top_score is not None:
        print(
            f"Top score            : "
            f"{float(top_score):.2f}/100"
        )

    else:
        print(
            "Top score            : N/A"
        )

    print()
    print("FILES")
    print("-" * 92)

    print(
        f"Pipeline report      : "
        f"{files.get('pipeline_report') or 'N/A'}"
    )

    print(
        f"Latest report        : "
        f"{files.get('latest_pipeline_report') or 'N/A'}"
    )

    print(
        f"Recommendation       : "
        f"{recommendation_summary.get('report_path') or 'N/A'}"
    )

    print(
        f"Latest recommendation: "
        f"{recommendation_summary.get('latest_path') or 'N/A'}"
    )

    print(
        f"Execution log        : "
        f"{files.get('log_file') or 'N/A'}"
    )

    print("=" * 92)

    print()
    print(
        "주의: 이 시스템은 실험적 머신러닝 모델과 "
        "기술적·통계적 계산을 이용한 참고 분석입니다."
    )

    print(
        "투자 조언, 실제 주문 지시 또는 "
        "수익 보장이 아닙니다."
    )


def run_daily_pipeline(
    symbols: list[str],
    prediction_period: str = "5y",
    prediction_interval: str = "1d",
    neutral_threshold_percent: float = 1.0,
    continue_after_step_error: bool = True,
) -> dict[str, Any]:
    """
    V6.1 Daily Automation Pipeline 전체 실행 함수입니다.

    실행 순서:

    1. 저장 모델을 이용한 최신 일일 예측
    2. 예측 이력 추가
    3. 평가 가능한 과거 예측 결과 확인
    4. 누적 정확도 저장
    5. Recommendation Engine 실행
    6. 진입 구간, 손절가, 목표가 계산
    7. 추천 등급과 추천 비중 계산
    8. Pipeline 보고서 및 로그 저장
    """

    cleaned_symbols = normalize_symbols(
        symbols
    )

    if not cleaned_symbols:
        raise ValueError(
            "Daily Pipeline에서 처리할 "
            "종목이 없습니다."
        )

    if neutral_threshold_percent < 0:
        raise ValueError(
            "neutral_threshold_percent는 "
            "0 이상이어야 합니다."
        )

    ensure_directories()

    started_at = datetime.now()

    log_path = build_daily_log_path(
        started_at
    )

    append_log(
        message=(
            "V6.1 DAILY PIPELINE STARTED"
        ),
        log_path=log_path,
    )

    print()
    print("=" * 92)
    print(
        "AI STOCK BOT V6.1 "
        "DAILY PIPELINE STARTED"
    )
    print("=" * 92)

    print(
        f"Started at           : "
        f"{started_at.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print(
        f"Symbols              : "
        f"{', '.join(cleaned_symbols)}"
    )

    print(
        f"Total symbols        : "
        f"{len(cleaned_symbols)}"
    )

    print("=" * 92)

    steps: list[
        PipelineStepResult
    ] = []

    # -------------------------------------------------
    # STEP 1: Daily Prediction
    # -------------------------------------------------

    prediction_step = run_pipeline_step(
        step_name="DAILY_PREDICTIONS",

        function=(
            generate_daily_predictions
        ),

        log_path=log_path,

        symbols=cleaned_symbols,

        period=prediction_period,
        interval=prediction_interval,

        continue_on_error=True,
        save_reports=True,
    )

    steps.append(
        prediction_step
    )

    # -------------------------------------------------
    # STEP 2: Prediction Tracker
    # -------------------------------------------------

    if (
        not prediction_step.success
        and not continue_after_step_error
    ):
        tracker_step = create_skipped_step(
            step_name="PREDICTION_TRACKER",

            reason=(
                "Daily Prediction 단계가 실패하여 "
                "Prediction Tracker를 실행하지 않았습니다."
            ),
        )

        append_log(
            message=(
                "STEP SKIPPED: PREDICTION_TRACKER | "
                "Previous step failed."
            ),
            log_path=log_path,
        )

    else:
        tracker_step = run_pipeline_step(
            step_name="PREDICTION_TRACKER",

            function=(
                run_prediction_tracker
            ),

            log_path=log_path,

            neutral_threshold_percent=(
                neutral_threshold_percent
            ),
        )

    steps.append(
        tracker_step
    )

    # -------------------------------------------------
    # STEP 3: Recommendation Engine
    # -------------------------------------------------

    if (
        not prediction_step.success
        and not continue_after_step_error
    ):
        recommendation_step = create_skipped_step(
            step_name="RECOMMENDATION_ENGINE",

            reason=(
                "Daily Prediction 단계가 실패하여 "
                "Recommendation Engine을 실행하지 않았습니다."
            ),
        )

        append_log(
            message=(
                "STEP SKIPPED: RECOMMENDATION_ENGINE | "
                "Previous prediction step failed."
            ),
            log_path=log_path,
        )

    else:
        recommendation_step = run_pipeline_step(
            step_name="RECOMMENDATION_ENGINE",

            function=(
                generate_recommendations
            ),

            log_path=log_path,
        )

    steps.append(
        recommendation_step
    )

    # -------------------------------------------------
    # Pipeline 최종 결과 계산
    # -------------------------------------------------

    finished_at = datetime.now()

    elapsed_seconds = (
        finished_at
        - started_at
    ).total_seconds()

    successful_steps = sum(
        1
        for step in steps
        if step.success
    )

    failed_steps = (
        len(steps)
        - successful_steps
    )

    if failed_steps == 0:
        pipeline_status = "SUCCESS"

    elif successful_steps > 0:
        pipeline_status = (
            "PARTIAL_SUCCESS"
        )

    else:
        pipeline_status = "FAILED"

    prediction_summary = (
        get_prediction_summary(
            prediction_step
        )
    )

    tracker_summary = (
        get_tracker_summary(
            tracker_step
        )
    )

    recommendation_summary = (
        get_recommendation_summary(
            recommendation_step
        )
    )

    report: dict[str, Any] = {
        "version": "V6.1",

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

            "prediction_period": (
                prediction_period
            ),

            "prediction_interval": (
                prediction_interval
            ),

            "neutral_threshold_percent": (
                neutral_threshold_percent
            ),

            "continue_after_step_error": (
                continue_after_step_error
            ),
        },

        "summary": {
            "pipeline_status": (
                pipeline_status
            ),

            "total_steps": len(
                steps
            ),

            "successful_steps": (
                successful_steps
            ),

            "failed_steps": (
                failed_steps
            ),
        },

        "prediction_summary": (
            prediction_summary
        ),

        "tracker_summary": (
            tracker_summary
        ),

        "recommendation_summary": (
            recommendation_summary
        ),

        "steps": [
            step.to_dict()
            for step in steps
        ],

        "files": {},

        "disclaimer": (
            "This pipeline produces experimental machine-learning, "
            "technical-analysis and statistical reference results. "
            "It is not investment advice, an order instruction or "
            "a guarantee of returns."
        ),
    }

    (
        dated_report_path,
        latest_report_path,
    ) = save_pipeline_report(
        report=report,
        finished_at=finished_at,
    )

    report["files"] = {
        "pipeline_report": str(
            dated_report_path
        ),

        "latest_pipeline_report": str(
            latest_report_path
        ),

        "log_file": str(
            log_path
        ),

        "recommendation_report": (
            recommendation_summary.get(
                "report_path"
            )
        ),

        "latest_recommendation_report": (
            recommendation_summary.get(
                "latest_path"
            )
        ),
    }

    # files 경로가 포함된 최종 보고서를 다시 저장합니다.
    save_json_file(
        path=dated_report_path,
        data=report,
    )

    save_json_file(
        path=latest_report_path,
        data=report,
    )

    append_log(
        message=(
            f"V6.1 DAILY PIPELINE FINISHED | "
            f"STATUS={pipeline_status} | "
            f"SUCCESSFUL_STEPS={successful_steps} | "
            f"FAILED_STEPS={failed_steps} | "
            f"ELAPSED={elapsed_seconds:.2f}s"
        ),
        log_path=log_path,
    )

    print_pipeline_summary(
        report
    )

    return report