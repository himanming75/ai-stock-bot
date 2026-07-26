import sys
from datetime import datetime
from pathlib import Path

from automation.daily_pipeline import run_daily_pipeline
from config import SYMBOLS


PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIRECTORY = PROJECT_ROOT / "logs"
SCHEDULER_LOG_PATH = LOG_DIRECTORY / "scheduler_runner.log"


def write_scheduler_log(
    message: str,
) -> None:
    """
    Windows Task Scheduler 실행 기록을 저장합니다.
    """

    LOG_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    with SCHEDULER_LOG_PATH.open(
        mode="a",
        encoding="utf-8",
    ) as file:
        file.write(
            f"[{timestamp}] {message}\n"
        )


def main() -> int:
    """
    Windows Task Scheduler에서 실행할
    V5.5 Daily Pipeline 진입점입니다.
    """

    write_scheduler_log(
        "Scheduled daily pipeline started."
    )

    try:
        report = run_daily_pipeline(
            symbols=SYMBOLS,
            prediction_period="5y",
            prediction_interval="1d",
            neutral_threshold_percent=1.0,
            continue_after_step_error=True,
        )

        pipeline_status = (
            report.get(
                "summary",
                {},
            ).get(
                "pipeline_status",
                "UNKNOWN",
            )
        )

        write_scheduler_log(
            "Scheduled daily pipeline finished. "
            f"Status={pipeline_status}"
        )

        if pipeline_status in {
            "SUCCESS",
            "PARTIAL_SUCCESS",
        }:
            return 0

        return 1

    except KeyboardInterrupt:
        write_scheduler_log(
            "Scheduled daily pipeline cancelled."
        )

        return 130

    except Exception as error:
        write_scheduler_log(
            "Scheduled daily pipeline failed. "
            f"{type(error).__name__}: {error}"
        )

        return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )