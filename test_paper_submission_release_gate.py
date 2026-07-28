import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.paper_submission_release_gate import (
    PaperSubmissionReleasePolicy,
    load_release_result,
    release_paper_submission,
    save_release_result,
    verify_release,
)
from test_paper_submission_reconciliation import build, create_sources


NOW = datetime(2026, 7, 27, 21, 30, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_source() -> Any:
    translation, submission = create_sources()
    return build(translation, submission)


def issue(
    source: Any,
    operator: str | None = None,
    text: str = "RELEASE RECONCILED PAPER SUBMISSION",
    existing: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    actual = operator or source.report.operator
    return silent(
        release_paper_submission,
        source,
        actual,
        text,
        existing,
        policy,
        now,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_safe(result: Any) -> None:
    require(all((
        not result.paper_execution_authorized,
        not result.automatic_execution_authorized,
        result.execution_blocked,
        not result.network_accessed,
        not result.account_accessed,
        not result.broker_api_called,
        not result.broker_order_created,
        not result.order_submitted,
        not result.live_order_created,
        not result.live_execution_authorized,
    )), "실행 안전장치가 해제되었습니다.")


def main() -> None:
    source = create_source()
    released = issue(source)
    require(
        released.result_status == "PAPER_RELEASED",
        "정상 Release가 실패했습니다.",
    )
    require(released.paper_submission_released, "Release가 설정되지 않았습니다.")
    require(released.released_item_count == 2, "Release Item 수가 다릅니다.")
    require(len(released.releases) == 1, "Release Record가 생성되지 않았습니다.")
    valid, time_valid, errors = verify_release(released.releases[0], NOW)
    require(valid and time_valid and not errors, "Release 검사가 실패했습니다.")
    require_safe(released)

    wrong_operator = issue(source, operator="wrong")
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = issue(source, text="IGNORE")
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    duplicate = issue(source, existing=released.releases)
    require(duplicate.result_status == "BLOCKED", "중복 Release가 차단되지 않았습니다.")

    unsafe_policy = PaperSubmissionReleasePolicy(order_submission_disabled=False)
    unsafe = issue(source, policy=unsafe_policy)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    tampered_source = copy.deepcopy(source)
    object.__setattr__(
        tampered_source.report,
        "reconciled_count",
        0,
    )
    tampered = issue(tampered_source)
    require(tampered.result_status == "FAILED", "변조 Source가 실패 처리되지 않았습니다.")

    expired_release = released.releases[0]
    expired_valid, expired_time, expired_errors = verify_release(
        expired_release,
        NOW + timedelta(minutes=11),
    )
    require(
        not expired_valid and not expired_time and expired_errors,
        "만료 Release가 차단되지 않았습니다.",
    )

    changed_release = replace(
        released.releases[0],
        released_item_count=99,
    )
    changed_valid, _, changed_errors = verify_release(changed_release, NOW)
    require(
        not changed_valid and changed_errors,
        "Release 변조가 탐지되지 않았습니다.",
    )

    bad_existing = issue(source, existing=(changed_release,))
    require(
        bad_existing.result_status == "BLOCKED",
        "위험 Existing Release가 차단되지 않았습니다.",
    )

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_release_result(released, Path(directory))
        require(report.exists() and latest.exists(), "결과가 저장되지 않았습니다.")
        payload = load_release_result(latest)
        require(payload["version"] == "V13.7", "저장 Version이 다릅니다.")

    for result in (
        released,
        wrong_operator,
        wrong_text,
        duplicate,
        unsafe,
        tampered,
        bad_existing,
    ):
        require_safe(result)

    checks = {
        "Version is V13.7": released.version == "V13.7",
        "Default policy is valid": released.policy_checks_passed,
        "Policy is immutable": PaperSubmissionReleasePolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V13.6 source was validated": released.source_checks_passed,
        "Reconciliation report hash passed": released.report_checks_passed,
        "Paper submission was released": released.paper_submission_released,
        "Two reconciled items were released": released.released_item_count == 2,
        "Release hash passed": valid,
        "Release expiration was calculated": time_valid,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Duplicate release was blocked": duplicate.result_status == "BLOCKED",
        "Tampered source failed": tampered.result_status == "FAILED",
        "Expired release was blocked": not expired_valid,
        "Release tampering detected": not changed_valid,
        "Unsafe existing release was blocked": bad_existing.result_status == "BLOCKED",
        "Result save and load passed": payload["version"] == "V13.7",
        "Paper execution remains unauthorized": not released.paper_execution_authorized,
        "Broker API was not called": not released.broker_api_called,
        "Broker order was not created": not released.broker_order_created,
        "Order was not submitted": not released.order_submitted,
        "Live execution not authorized": not released.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V13.7 PAPER SUBMISSION RELEASE GATE TEST")
    print("=" * 92)
    print("V13.7 VALIDATION CHECKS")
    print("-" * 92)
    for name, passed in checks.items():
        print(f"{name:<58}: {passed}")
    print("=" * 92)
    require(checks["All checks passed"], "V13.7 Validation Check가 실패했습니다.")
    print()
    print("V13.7 paper submission release gate test completed successfully.")
    print("V13.6 Source, 수동 Release, SHA-256 봉인, 만료 및 중복 차단이 검증되었습니다.")
    print("Broker API, 실제 주문 제출 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
