import contextlib
import copy
import io
import tempfile
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backtest.paper_submission_final_control import (
    PaperSubmissionFinalControlPolicy,
    load_final_control_result,
    run_paper_submission_final_control,
    save_final_control_result,
    verify_control_seal,
)
from test_paper_submission_release_gate import create_source, issue
from test_paper_submission_release_ledger import record


NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def silent(function: Any, *args: Any, **kwargs: Any) -> Any:
    with contextlib.redirect_stdout(io.StringIO()):
        return function(*args, **kwargs)


def create_sources(now: datetime = NOW) -> tuple[Any, Any, Any]:
    reconciliation = create_source()
    release = issue(reconciliation, now=now)
    ledger = record(release, now=now)
    return reconciliation, release, ledger


def control(
    reconciliation: Any,
    release: Any,
    ledger: Any,
    operator: str | None = None,
    text: str = "PASS PAPER SUBMISSION FINAL CONTROL",
    existing: Any = None,
    policy: Any = None,
    now: datetime = NOW,
) -> Any:
    actual = operator or release.releases[-1].operator
    return silent(
        run_paper_submission_final_control,
        reconciliation,
        release,
        ledger,
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
    reconciliation, release, ledger = create_sources()
    passed = control(reconciliation, release, ledger)
    require(
        passed.result_status == "FINAL_CONTROL_PASSED",
        "정상 Final Control이 실패했습니다.",
    )
    require(passed.final_control_passed, "Final Control이 통과하지 않았습니다.")
    require(passed.controlled_item_count == 2, "Control Item 수가 다릅니다.")
    require(len(passed.controls) == 1, "Control Seal이 생성되지 않았습니다.")
    valid, errors = verify_control_seal(passed.controls[0])
    require(valid and not errors, "Control Seal 검사가 실패했습니다.")
    require_safe(passed)

    wrong_operator = control(
        reconciliation, release, ledger, operator="wrong"
    )
    require(wrong_operator.result_status == "BLOCKED", "잘못된 Operator가 차단되지 않았습니다.")
    wrong_text = control(
        reconciliation, release, ledger, text="IGNORE"
    )
    require(wrong_text.result_status == "BLOCKED", "잘못된 확인 문구가 차단되지 않았습니다.")
    duplicate = control(
        reconciliation,
        release,
        ledger,
        existing=passed.controls,
    )
    require(duplicate.result_status == "BLOCKED", "중복 Control이 차단되지 않았습니다.")

    unsafe_policy = PaperSubmissionFinalControlPolicy(order_submission_disabled=False)
    unsafe = control(
        reconciliation, release, ledger, policy=unsafe_policy
    )
    require(not unsafe.all_checks_passed, "위험 Policy가 차단되지 않았습니다.")

    other_reconciliation, other_release, other_ledger = create_sources()
    mismatch = control(reconciliation, release, other_ledger)
    require(mismatch.result_status == "BLOCKED", "불일치 Ledger 연결이 차단되지 않았습니다.")

    tampered_reconciliation = copy.deepcopy(reconciliation)
    object.__setattr__(
        tampered_reconciliation.report,
        "reconciled_count",
        99,
    )
    tampered_source = control(
        tampered_reconciliation, release, ledger
    )
    require(
        tampered_source.result_status == "FAILED",
        "변조 Reconciliation이 실패 처리되지 않았습니다.",
    )

    changed_seal = replace(
        passed.controls[0],
        controlled_item_count=99,
    )
    changed_valid, changed_errors = verify_control_seal(changed_seal)
    require(
        not changed_valid and changed_errors,
        "Control Seal 변조가 탐지되지 않았습니다.",
    )
    unsafe_existing = control(
        reconciliation,
        release,
        ledger,
        existing=(changed_seal,),
    )
    require(
        unsafe_existing.result_status == "BLOCKED",
        "변조 Existing Control이 차단되지 않았습니다.",
    )

    expired = control(
        reconciliation,
        release,
        ledger,
        now=NOW + timedelta(minutes=11),
    )
    require(expired.result_status == "FAILED", "만료 Release가 실패 처리되지 않았습니다.")

    with tempfile.TemporaryDirectory() as directory:
        report, latest = save_final_control_result(
            passed, Path(directory)
        )
        require(report.exists() and latest.exists(), "Control 결과가 저장되지 않았습니다.")
        payload = load_final_control_result(latest)
        require(payload["version"] == "V13.9", "저장 Version이 다릅니다.")

    for result in (
        passed,
        wrong_operator,
        wrong_text,
        duplicate,
        unsafe,
        mismatch,
        tampered_source,
        unsafe_existing,
        expired,
    ):
        require_safe(result)

    checks = {
        "Version is V13.9": passed.version == "V13.9",
        "Default policy is valid": passed.policy_checks_passed,
        "Policy is immutable": PaperSubmissionFinalControlPolicy.__dataclass_params__.frozen,
        "Invalid policies are blocked": not unsafe.all_checks_passed,
        "V13.6 reconciliation passed": passed.reconciliation_checks_passed,
        "V13.7 release passed": passed.release_checks_passed,
        "V13.8 ledger passed": passed.ledger_checks_passed,
        "All source identities were linked": passed.linkage_checks_passed,
        "Source chronology passed": passed.chronology_checks_passed,
        "Final control seal was created": passed.final_control_passed,
        "Two items were controlled": passed.controlled_item_count == 2,
        "Control seal hash passed": valid,
        "Wrong operator was blocked": wrong_operator.result_status == "BLOCKED",
        "Wrong confirmation was blocked": wrong_text.result_status == "BLOCKED",
        "Duplicate control was blocked": duplicate.result_status == "BLOCKED",
        "Mismatched ledger was blocked": mismatch.result_status == "BLOCKED",
        "Tampered reconciliation failed": tampered_source.result_status == "FAILED",
        "Control seal tampering detected": not changed_valid,
        "Unsafe existing control was blocked": unsafe_existing.result_status == "BLOCKED",
        "Expired release failed": expired.result_status == "FAILED",
        "Result save and load passed": payload["version"] == "V13.9",
        "Paper execution remains unauthorized": not passed.paper_execution_authorized,
        "Broker API was not called": not passed.broker_api_called,
        "Broker order was not created": not passed.broker_order_created,
        "Order was not submitted": not passed.order_submitted,
        "Live execution not authorized": not passed.live_execution_authorized,
    }
    checks["All checks passed"] = all(checks.values())
    print("=" * 92)
    print("AI STOCK BOT V13.9 PAPER SUBMISSION FINAL CONTROL TEST")
    print("=" * 92)
    print("V13.9 VALIDATION CHECKS")
    print("-" * 92)
    for name, result in checks.items():
        print(f"{name:<58}: {result}")
    print("=" * 92)
    require(checks["All checks passed"], "V13.9 Validation Check가 실패했습니다.")
    print()
    print("V13.9 paper submission final control test completed successfully.")
    print("V13.6~V13.8 ID·Hash·시간 연결, 최종 봉인 및 변조 차단이 검증되었습니다.")
    print("Broker API, 실제 주문 제출 및 Live Execution은 호출되지 않았습니다.")


if __name__ == "__main__":
    main()
