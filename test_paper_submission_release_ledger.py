import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.paper_submission_release_ledger import (
    PaperSubmissionReleaseLedgerPolicy,
    load_ledger_result,
    record_paper_submission_release,
    save_ledger_result,
    verify_ledger_chain,
)
from test_paper_submission_release_gate import create_source, issue


NOW = datetime(2026, 7, 27, 21, 40, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_release(now: datetime = NOW) -> Any:
    return issue(create_source(), now=now)


def record(
    source: Any,
    operator: str | None = None,
    text: str = "RECORD PAPER SUBMISSION RELEASE",
    existing: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    actual = operator or source.releases[-1].operator
    return silent(
        record_paper_submission_release,
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
    first_release = create_release(NOW)
    first = record(first_release, now=NOW)
    require(first.result_status == "RECORDED", "첫 Ledger 기록이 실패했습니다.")
    require(first.total_entry_count == 1, "첫 Ledger 개수가 다릅니다.")
    require(first.entries[0].sequence == 1, "Genesis Sequence가 다릅니다.")
    require_safe(first)

    second_time = NOW + timedelta(minutes=1)
    second_release = create_release(second_time)
    second = record(
        second_release,
        existing=first.entries,
        now=second_time,
    )
    require(second.result_status == "RECORDED", "두 번째 Ledger 기록이 실패했습니다.")
    require(second.total_entry_count == 2, "두 Ledger Entry가 생성되지 않았습니다.")
    valid_chain, chain_errors = verify_ledger_chain(second.entries)
    require(valid_chain and not chain_errors, "Ledger Hash Chain이 실패했습니다.")
    require_safe(second)

    duplicate = record(
        first_release,
        existing=first.entries,
        now=second_time,
    )
    require(duplicate.result_status == "BLOCKED", "중복 Release가 차단되지 않았습니다.")
    wrong_operator = record(first_release, operator="wrong", now=NOW)
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = record(first_release, text="IGNORE", now=NOW)
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")

    unsafe_policy = PaperSubmissionReleaseLedgerPolicy(order_submission_disabled=False)
    unsafe = record(first_release, policy=unsafe_policy, now=NOW)
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    late_release = create_release(NOW)
    backward = record(
        late_release,
        existing=first.entries,
        now=NOW - timedelta(seconds=1),
    )
    require(backward.result_status == "BLOCKED", "역순 시간이 차단되지 않았습니다.")

    changed_entry = replace(second.entries[0], released_item_count=99)
    changed_entries = (changed_entry, second.entries[1])
    changed_valid, changed_errors = verify_ledger_chain(changed_entries)
    require(not changed_valid and changed_errors, "Ledger 변조가 탐지되지 않았습니다.")
    unsafe_existing = record(
        create_release(second_time),
        existing=changed_entries,
        now=second_time,
    )
    require(
        unsafe_existing.result_status == "BLOCKED",
        "변조 Existing Ledger가 차단되지 않았습니다.",
    )

    tampered_release = copy.deepcopy(first_release)
    object.__setattr__(
        tampered_release.releases[-1],
        "released_item_count",
        99,
    )
    tampered = record(tampered_release, now=NOW)
    require(tampered.result_status == "FAILED", "변조 Release가 실패 처리되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_ledger_result(second, Path(directory))
        require(report.exists() and latest.exists(), "Ledger 결과가 저장되지 않았습니다.")
        payload = load_ledger_result(latest)
        require(payload["version"] == "V13.8", "저장 Version이 다릅니다.")

    for result in (
        first,
        second,
        duplicate,
        wrong_operator,
        wrong_text,
        unsafe,
        backward,
        unsafe_existing,
        tampered,
    ):
        require_safe(result)

    checks = {
        "Version is V13.8": second.version == "V13.8",
        "Default policy is valid": second.policy_checks_passed,
        "Policy is immutable": PaperSubmissionReleaseLedgerPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "First release was recorded": first.ledger_entry_recorded,
        "Second release was recorded": second.ledger_entry_recorded,
        "Two ledger entries were created": second.total_entry_count == 2,
        "Sequences are chronological": [x.sequence for x in second.entries] == [1, 2],
        "SHA-256 hash chain passed": valid_chain,
        "Duplicate release was blocked": duplicate.result_status == "BLOCKED",
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Backward time was blocked": backward.result_status == "BLOCKED",
        "Ledger tampering detected": not changed_valid,
        "Unsafe existing ledger was blocked": unsafe_existing.result_status == "BLOCKED",
        "Tampered release failed": tampered.result_status == "FAILED",
        "Result save and load passed": payload["version"] == "V13.8",
        "Paper execution remains unauthorized": not second.paper_execution_authorized,
        "Broker API was not called": not second.broker_api_called,
        "Broker order was not created": not second.broker_order_created,
        "Order was not submitted": not second.order_submitted,
        "Live execution not authorized": not second.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V13.8 PAPER SUBMISSION RELEASE LEDGER TEST")
    print("=" * 92)
    print("V13.8 VALIDATION CHECKS")
    print("-" * 92)
    for name, passed in checks.items():
        print(f"{name:<58}: {passed}")
    print("=" * 92)
    require(checks["All checks passed"], "V13.8 Validation Check가 실패했습니다.")
    print()
    print("V13.8 paper submission release ledger test completed successfully.")
    print("Release 누적, Sequence, SHA-256 Hash Chain, 중복·역순·변조 차단이 검증되었습니다.")
    print("Broker API, 실제 주문 제출 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
